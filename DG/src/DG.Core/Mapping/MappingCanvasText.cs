namespace DG.Core.Mapping;

/// <summary>A canvas group: its name and the instance ids it contains (objects or other groups).</summary>
public sealed record CanvasGroupInfo(Guid Id, string Name, IReadOnlyList<Guid> Members);

/// <summary>A scribble with its text and canvas centre.</summary>
public sealed record CanvasScribbleInfo(Guid Id, string Text, float X, float Y);

/// <summary>Canvas rectangle of an object (pivot-free bounds as Grasshopper reports them).</summary>
public readonly record struct CanvasBounds(float X, float Y, float Width, float Height)
{
    public float CenterX => X + Width / 2f;

    public float CenterY => Y + Height / 2f;

    /// <summary>Distance from a point to the rectangle (0 inside).</summary>
    public float DistanceTo(float x, float y)
    {
        var dx = Math.Max(Math.Max(X - x, 0f), x - (X + Width));
        var dy = Math.Max(Math.Max(Y - y, 0f), y - (Y + Height));
        return MathF.Sqrt(dx * dx + dy * dy);
    }
}

/// <summary>
/// Pure helpers that turn Grasshopper canvas text into mapping evidence (owner amendment
/// 2026-10-18: group names, scribble text and component names take part in mapping).
/// No Grasshopper SDK dependency; DG.Grasshopper feeds it plain records.
/// </summary>
public static class MappingCanvasText
{
    /// <summary>Scribbles farther than this (canvas units) from an object are not its annotation.</summary>
    public const float ScribbleRadius = 250f;

    private const int MaxNames = 12;

    /// <summary>
    /// Object id → names of every group that contains it, directly or through nested groups,
    /// innermost first. Group names that are empty or whitespace are skipped.
    /// </summary>
    public static Dictionary<Guid, List<string>> GroupNamesByObject(IReadOnlyList<CanvasGroupInfo> groups)
    {
        var byId = groups.ToDictionary(g => g.Id);
        var parents = new Dictionary<Guid, List<CanvasGroupInfo>>();
        foreach (var g in groups)
        {
            foreach (var m in g.Members)
            {
                if (!parents.TryGetValue(m, out var list))
                {
                    parents[m] = list = new List<CanvasGroupInfo>();
                }

                list.Add(g);
            }
        }

        var result = new Dictionary<Guid, List<string>>();
        foreach (var member in parents.Keys)
        {
            if (byId.ContainsKey(member))
            {
                continue; // groups themselves are not mappable objects
            }

            var names = new List<string>();
            var seen = new HashSet<Guid>();
            var queue = new Queue<CanvasGroupInfo>(parents[member]);
            while (queue.Count > 0)
            {
                var g = queue.Dequeue();
                if (!seen.Add(g.Id))
                {
                    continue;
                }

                var name = Clean(g.Name);
                if (name.Length > 0 && !names.Contains(name, StringComparer.Ordinal))
                {
                    names.Add(name);
                }

                if (parents.TryGetValue(g.Id, out var outer))
                {
                    foreach (var o in outer)
                    {
                        queue.Enqueue(o);
                    }
                }
            }

            result[member] = names;
        }

        return result;
    }

    /// <summary>
    /// Scribble texts that annotate an object: scribbles in one of its groups, then scribbles
    /// within <see cref="ScribbleRadius"/> of its bounds, nearest first.
    /// </summary>
    public static List<string> ScribblesFor(
        Guid objectId,
        CanvasBounds bounds,
        IReadOnlyList<CanvasScribbleInfo> scribbles,
        IReadOnlyList<CanvasGroupInfo> groups)
    {
        var sameGroup = new HashSet<Guid>(groups.Where(g => g.Members.Contains(objectId)).SelectMany(g => g.Members));
        return scribbles
            .Select(s => (s, d: sameGroup.Contains(s.Id) ? 0f : bounds.DistanceTo(s.X, s.Y)))
            .Where(t => t.d <= ScribbleRadius && Clean(t.s.Text).Length > 0)
            .OrderBy(t => t.d)
            .ThenBy(t => t.s.Text, StringComparer.Ordinal)
            .Select(t => Clean(t.s.Text))
            .Distinct(StringComparer.Ordinal)
            .Take(3)
            .ToList();
    }

    /// <summary>True when a nickname carries no meaning of its own (empty or the default name/abbreviation).</summary>
    public static bool IsDefaultNickname(string? nickname, string? name, string? defaultNickname = null)
    {
        var nick = Clean(nickname);
        return nick.Length == 0
            || string.Equals(nick, Clean(name), StringComparison.OrdinalIgnoreCase)
            || (defaultNickname is not null && string.Equals(nick, Clean(defaultNickname), StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>Distinct, non-empty names in order, at most <see cref="MaxNames"/>.</summary>
    public static List<string> Merge(params IEnumerable<string?>[] sources)
    {
        var names = new List<string>();
        foreach (var source in sources)
        {
            foreach (var raw in source)
            {
                var text = Clean(raw);
                if (text.Length > 0 && !names.Contains(text, StringComparer.Ordinal))
                {
                    names.Add(text);
                }
            }
        }

        return names.Take(MaxNames).ToList();
    }

    /// <summary>Single-line, trimmed text of at most 120 characters.</summary>
    public static string Clean(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return string.Empty;
        }

        var single = string.Join(" ", text.Split(new[] { '\r', '\n', '\t' }, StringSplitOptions.RemoveEmptyEntries)).Trim();
        return single.Length <= 120 ? single : single[..120];
    }
}
