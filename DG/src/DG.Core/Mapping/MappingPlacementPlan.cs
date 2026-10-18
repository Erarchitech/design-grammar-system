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
/// class, one RULE BY ID + PROPERTY STATE per rule binding, one PARAMETER STATE for the DG
/// parameters, then DESIGN STATE and VALIDATOR. Pure: built from the apply result only.
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

        var classes = rolesOfStream
            .Where(kv => !split.Contains(kv.Key))
            .SelectMany(kv => kv.Value.Select(cls => (cls, stream: kv.Key)))
            .GroupBy(t => t.cls, StringComparer.Ordinal)
            .OrderBy(g => MappingSessionClient.LocalName(g.Key), StringComparer.Ordinal)
            .Select(g => new PlacedClass(g.Key, MappingSessionClient.LocalName(g.Key) ?? g.Key, g.Select(t => t.stream).Distinct(StringComparer.Ordinal).OrderBy(s => s, StringComparer.Ordinal).ToList()))
            .ToList();

        var placedClasses = new HashSet<string>(classes.Select(c => c.ClassIri), StringComparer.Ordinal);
        var bindings = new List<PlacedBinding>();
        foreach (var b in applied.Bindings.OrderBy(b => b.RuleId, StringComparer.Ordinal))
        {
            if (!placedClasses.Contains(b.ClassIri))
            {
                notes.Add($"rule {b.RuleId}: class {MappingSessionClient.LocalName(b.ClassIri)} has no OBJECT STATE");
                continue;
            }

            bindings.Add(new PlacedBinding(b.RuleId, b.ClassIri, b.PropertyIri, LastSegment(b.MeasureId), b.Stream));
        }

        var parameters = applied.Parameters
            .Select(p => new PlacedParameter(LastSegment(p.NativeId), p.Name))
            .OrderBy(p => p.Name, StringComparer.Ordinal)
            .ToList();

        return new MappingPlacementPlan { Classes = classes, Bindings = bindings, Parameters = parameters, Notes = notes };
    }
}
