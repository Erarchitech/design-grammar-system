namespace DG.Core.Mapping;

/// <summary>
/// "class:&lt;IRI&gt;" — how an automatically placed OBJECT STATE names its class (1303-CONTEXT
/// D-38). The class is bound by identity and stored in the .gh, so adding classes to the
/// ontology cannot shift it, unlike METAGRAPH Objects + List Item(index).
/// </summary>
public static class MappingClassText
{
    public const string Prefix = "class:";

    public static string For(string iri) => Prefix + iri;

    public static string? Parse(string? text)
    {
        if (text is null)
        {
            return null;
        }

        var t = text.Trim();
        return t.StartsWith(Prefix, StringComparison.Ordinal) && t.Length > Prefix.Length ? t[Prefix.Length..].Trim() : null;
    }
}

/// <summary>One OBJECT STATE to place: the class and the element streams (param instance ids) that feed it.</summary>
public sealed record PlacedClass(string ClassIri, string Label, IReadOnlyList<string> Streams);

/// <summary>One PROPERTY STATE to place: rule, class, property and the calculation output (param instance id).</summary>
public sealed record PlacedBinding(string RuleId, string ClassIri, string PropertyIri, string MeasureParam, string Stream);

/// <summary>One PARAMETER STATE input: the slider (instance id) and its ParameterId (the slider's name).</summary>
public sealed record PlacedParameter(string SliderGuid, string Name);

/// <summary>
/// What CONNECTOR places after the mapping is agreed (Phase 1303, D-38): one OBJECT STATE per
/// class and measured stream (per class when none of its rules is measured), one RULE BY ID +
/// PROPERTY STATE per rule binding, one PARAMETER STATE for the DG parameters, then DESIGN STATE
/// and VALIDATOR. Pure: built from the apply result only.
/// </summary>
public sealed class MappingPlacementPlan
{
    public IReadOnlyList<PlacedClass> Classes { get; init; } = Array.Empty<PlacedClass>();

    public IReadOnlyList<PlacedBinding> Bindings { get; init; } = Array.Empty<PlacedBinding>();

    public IReadOnlyList<PlacedParameter> Parameters { get; init; } = Array.Empty<PlacedParameter>();

    public IReadOnlyList<string> Notes { get; init; } = Array.Empty<string>();

    /// <summary>The last ':' segment of a native id ("gh:doc:measure:&lt;guid&gt;" → guid).</summary>
    public static string LastSegment(string nativeId)
    {
        var cut = nativeId.LastIndexOf(':');
        return cut >= 0 ? nativeId[(cut + 1)..] : nativeId;
    }

    /// <summary>Reject unsafe whole-stream wiring before any canvas write. Unaccepted members are never added.</summary>
    public static bool CoversWholeStreams(MappingApplyResult applied, MappingSnapshot snapshot)
    {
        var original = snapshot.Elements.ToDictionary(e => e.NativeId, StringComparer.Ordinal);
        if (applied.RolesByElement.Any(kv => !original.TryGetValue(kv.Key, out var e)
                || kv.Value.Count == 0 || !applied.ElementStreams.TryGetValue(kv.Key, out var stream) || stream != e.Stream))
        {
            return false;
        }

        var streams = applied.ElementStreams.Values.ToHashSet(StringComparer.Ordinal);
        return snapshot.Elements.Where(e => streams.Contains(e.Stream))
            .All(e => applied.RolesByElement.ContainsKey(e.NativeId));
    }

    public static MappingPlacementPlan From(MappingApplyResult applied)
    {
        var notes = new List<string>();

        // Role set of every stream; a stream whose elements carry different role sets is split
        // between classes and cannot be wired whole into one OBJECT STATE.
        var rolesOfStream = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
        var split = new HashSet<string>(StringComparer.Ordinal);
        foreach (var (nativeId, roles) in applied.RolesByElement)
        {
            if (!applied.ElementStreams.TryGetValue(nativeId, out var stream) || string.IsNullOrEmpty(stream))
            {
                continue;
            }

            var set = new HashSet<string>(roles, StringComparer.Ordinal);
            if (rolesOfStream.TryGetValue(stream, out var existing))
            {
                if (!existing.SetEquals(set))
                {
                    split.Add(stream);
                }
            }
            else
            {
                rolesOfStream[stream] = set;
            }
        }

        foreach (var stream in split.OrderBy(s => s, StringComparer.Ordinal))
        {
            notes.Add($"stream {stream} is split between classes; it is not wired whole into an OBJECT STATE");
        }

        var streamsOfClass = rolesOfStream
            .Where(kv => !split.Contains(kv.Key))
            .SelectMany(kv => kv.Value.Select(cls => (cls, stream: kv.Key)))
            .GroupBy(t => t.cls, StringComparer.Ordinal)
            .OrderBy(g => MappingSessionClient.LocalName(g.Key), StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.Select(t => t.stream).Distinct(StringComparer.Ordinal).OrderBy(s => s, StringComparer.Ordinal).ToList(), StringComparer.Ordinal);

        // A PROPERTY STATE pairs one calculation output with the elements of one stream, so a class
        // whose rules are measured gets one OBJECT STATE per measured stream. Its unmeasured streams
        // would reach VALIDATOR without property values and are left out with a note.
        var bindings = new List<PlacedBinding>();
        var measured = new Dictionary<string, SortedSet<string>>(StringComparer.Ordinal);
        foreach (var b in applied.Bindings.OrderBy(b => b.RuleId, StringComparer.Ordinal))
        {
            var local = MappingSessionClient.LocalName(b.ClassIri);
            if (!streamsOfClass.TryGetValue(b.ClassIri, out var own))
            {
                notes.Add($"rule {b.RuleId}: class {local} has no OBJECT STATE");
                continue;
            }

            if (!own.Contains(b.Stream))
            {
                notes.Add($"rule {b.RuleId}: its calculation output follows stream {b.Stream}, not a stream of class {local}");
                continue;
            }

            bindings.Add(new PlacedBinding(b.RuleId, b.ClassIri, b.PropertyIri, LastSegment(b.MeasureId), b.Stream));
            if (!measured.TryGetValue(b.ClassIri, out var set))
            {
                measured[b.ClassIri] = set = new SortedSet<string>(StringComparer.Ordinal);
            }

            set.Add(b.Stream);
        }

        var classes = new List<PlacedClass>();
        foreach (var (cls, streams) in streamsOfClass)
        {
            var label = MappingSessionClient.LocalName(cls) ?? cls;
            if (!measured.TryGetValue(cls, out var withOutputs))
            {
                classes.Add(new PlacedClass(cls, label, streams));
                continue;
            }

            classes.AddRange(withOutputs.Select(s => new PlacedClass(cls, label, new[] { s })));
            foreach (var s in streams.Where(s => !withOutputs.Contains(s)))
            {
                notes.Add($"stream {s} of class {label} has no calculation output for its rules; it is not placed");
            }
        }

        var parameters = applied.Parameters
            .Select(p => new PlacedParameter(LastSegment(p.NativeId), p.Name))
            .OrderBy(p => p.Name, StringComparer.Ordinal)
            .ToList();

        return new MappingPlacementPlan { Classes = classes, Bindings = bindings, Parameters = parameters, Notes = notes };
    }
}
