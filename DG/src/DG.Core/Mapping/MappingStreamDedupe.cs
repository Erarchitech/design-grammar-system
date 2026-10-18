namespace DG.Core.Mapping;

/// <summary>
/// Streams that would map the same elements twice (Phase 1303, D-37): an exact duplicate of an
/// earlier stream (two Bounding Box outputs of the same facade), or a union of two or more
/// other streams ('All panels' = Panels A + Panels B). Elements are compared by a geometry key
/// "kind|bounding box". Duplicates need the same kind; a union is judged on the bounding box
/// alone, so module surfaces over the 6- and 5-module contours count as their union. Pure.
/// </summary>
public static class MappingStreamDedupe
{
    public const double ContainedShare = 0.9;

    private static string Box(string key)
    {
        var cut = key.IndexOf('|');
        return cut >= 0 ? key[(cut + 1)..] : key;
    }

    /// <param name="streams">Streams in reading order with the geometry keys of their elements.</param>
    /// <returns>Dropped stream → reason.</returns>
    public static Dictionary<string, string> Find(IReadOnlyList<(string Stream, string Label, IReadOnlyCollection<string> Keys)> streams)
    {
        var dropped = new Dictionary<string, string>(StringComparer.Ordinal);
        var sets = streams.Select(s => (s.Stream, s.Label, Keys: new HashSet<string>(s.Keys, StringComparer.Ordinal), Boxes: new HashSet<string>(s.Keys.Select(Box), StringComparer.Ordinal))).ToList();
        for (var i = 0; i < sets.Count; i++)
        {
            for (var j = 0; j < i; j++)
            {
                if (!dropped.ContainsKey(sets[j].Stream) && sets[i].Keys.Count > 0 && sets[i].Keys.SetEquals(sets[j].Keys))
                {
                    dropped[sets[i].Stream] = $"same elements as {sets[j].Label}";
                    break;
                }
            }
        }

        foreach (var s in sets)
        {
            if (dropped.ContainsKey(s.Stream) || s.Keys.Count == 0)
            {
                continue;
            }

            var parts = sets
                .Where(t => t.Stream != s.Stream && !dropped.ContainsKey(t.Stream) && t.Boxes.Count > 0 && t.Boxes.Count < s.Boxes.Count)
                .Where(t => t.Boxes.Count(k => s.Boxes.Contains(k)) >= ContainedShare * t.Boxes.Count)
                .Select(t => t.Label)
                .ToList();
            if (parts.Count >= 2)
            {
                dropped[s.Stream] = "union of " + string.Join(" + ", parts);
            }
        }

        return dropped;
    }
}
