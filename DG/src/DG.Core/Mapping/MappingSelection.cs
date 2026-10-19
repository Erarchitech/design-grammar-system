namespace DG.Core.Mapping;

/// <summary>The source address of one descriptor: a whole branch or one item of a single list.</summary>
public sealed record MappingSourceAddress(string Path, int Index, bool WholeBranch);

/// <summary>Exact class/stream partitions of explicitly committed elements, never inferred remainder.</summary>
public sealed record MappingSelectedClass(string ClassIri, string Stream, IReadOnlyList<string> ElementIds);

/// <summary>Class plus stable instance identity for selected GH elements.</summary>
public sealed class MappingObjectReference : DG.Core.Models.OntologyClass
{
    public string NativeId { get; init; } = string.Empty;
}

public static class MappingSelection
{
    public static IReadOnlyList<MappingSelectedClass> Classes(MappingApplyResult applied, MappingSnapshot snapshot)
    {
        var original = snapshot.Elements.ToDictionary(e => e.NativeId, StringComparer.Ordinal);
        var selected = new Dictionary<(string Class, string Stream), List<string>>();
        if (applied.ElementStreams.Count != applied.RolesByElement.Count)
        {
            throw new InvalidOperationException("Element streams must match the committed selection");
        }

        foreach (var (id, roles) in applied.RolesByElement)
        {
            if (!original.TryGetValue(id, out var element) || roles.Count == 0
                || roles.Any(string.IsNullOrWhiteSpace) || roles.Distinct(StringComparer.Ordinal).Count() != roles.Count
                || !applied.ElementStreams.TryGetValue(id, out var stream) || stream != element.Stream)
            {
                throw new InvalidOperationException("Committed element does not match the source snapshot");
            }

            foreach (var iri in roles)
            {
                var key = (iri, stream);
                if (!selected.TryGetValue(key, out var ids))
                {
                    selected[key] = ids = new List<string>();
                }

                ids.Add(id);
            }
        }

        return selected.OrderBy(kv => kv.Key.Class, StringComparer.Ordinal)
            .ThenBy(kv => kv.Key.Stream, StringComparer.Ordinal)
            .Select(kv => new MappingSelectedClass(kv.Key.Class, kv.Key.Stream,
                kv.Value.OrderBy(id => id, StringComparer.Ordinal).ToArray())).ToArray();
    }

    /// <summary>Resolve exact source rows, without broadening a missing item to its branch/stream.</summary>
    public static IReadOnlyList<IReadOnlyList<T>> Resolve<T>(IEnumerable<MappingSourceAddress> addresses,
        IReadOnlyDictionary<string, IReadOnlyList<T>> tree, bool measure)
    {
        var result = new List<IReadOnlyList<T>>();
        foreach (var address in addresses)
        {
            if (address.Index < 0 || !tree.TryGetValue(address.Path, out var branch) || branch.Count == 0)
                throw new InvalidOperationException("Selected branch was removed");
            if (address.WholeBranch && !measure)
            {
                result.Add(branch);
                continue;
            }
            var index = address.WholeBranch ? 0 : address.Index;
            if (address.WholeBranch && branch.Count != 1 || index >= branch.Count)
                throw new InvalidOperationException("Selected item no longer matches its element");
            result.Add(new[] { branch[index] });
        }
        return result;
    }

    /// <summary>Only successfully delivered history plus this immutable batch; no current draft state.</summary>
    public static MappingApplyResult Append(MappingApplyResult previous, MappingApplyResult current)
    {
        if (current.RolesByElement.Keys.Any(previous.RolesByElement.ContainsKey)
            || current.Parameters.Any(p => previous.Parameters.Any(old => old.NativeId == p.NativeId))
            || current.Measures.Any(m => previous.Measures.Any(old => old.NativeId == m.NativeId)))
            throw new InvalidOperationException("A later batch repeats an already delivered member");
        var roles = previous.RolesByElement.Concat(current.RolesByElement).ToDictionary(kv => kv.Key, kv => kv.Value, StringComparer.Ordinal);
        var streams = previous.ElementStreams.Concat(current.ElementStreams).ToDictionary(kv => kv.Key, kv => kv.Value, StringComparer.Ordinal);
        var measures = previous.Measures.Concat(current.Measures).ToArray();
        var bindings = previous.Bindings.Concat(current.Bindings).Distinct()
            .Where(b => measures.Any(m => m.NativeId == b.MeasureId && m.PropertyIri == b.PropertyIri)
                && roles.Any(kv => kv.Value.Contains(b.ClassIri) && streams.GetValueOrDefault(kv.Key) == b.Stream)).ToArray();
        return new MappingApplyResult
        {
            RolesByElement = roles, ElementStreams = streams, Measures = measures, Bindings = bindings,
            Parameters = previous.Parameters.Concat(current.Parameters).ToArray(),
        };
    }

    /// <summary>Resolve all selected addresses first; missing/duplicate addresses reject the entire selection.</summary>
    public static IReadOnlyList<MappingSourceAddress> Addresses(IEnumerable<string> ids,
        IReadOnlyDictionary<string, MappingSourceAddress> source)
    {
        var result = new List<MappingSourceAddress>();
        var seenIds = new HashSet<string>(StringComparer.Ordinal);
        var seenAddresses = new HashSet<MappingSourceAddress>();
        foreach (var id in ids)
        {
            if (!seenIds.Add(id) || !source.TryGetValue(id, out var address)
                || string.IsNullOrWhiteSpace(address.Path) || address.Index < 0 || !seenAddresses.Add(address))
            {
                throw new InvalidOperationException("Committed element address is absent or duplicated");
            }

            result.Add(address);
        }

        return result;
    }
}
