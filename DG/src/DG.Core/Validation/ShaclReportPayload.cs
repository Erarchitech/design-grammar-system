namespace DG.Core.Validation;

/// <summary>
/// The canonical SHACL report envelope returned by dg-reasoner's POST /shacl/validate,
/// relayed unmodified as the top-level `shacl` key of data-service's /validation/publish
/// response (Phase 823 Plan 02/03). Property names camelCase-match the JSON keys exactly
/// (System.Text.Json with JsonNamingPolicy.CamelCase silently nulls unmatched fields
/// instead of throwing -- RESEARCH.md Pitfall 4).
///
/// Defined here (DG.Core, public) rather than in DG.Grasshopper.Validation.ValidationPublishContract
/// so it is unit-testable from DG.Tests: DG.Tests targets net9.0 and cannot ProjectReference
/// DG.Grasshopper (net7.0-windows7.0 -- NU1201 TFM incompatibility confirmed during Plan 823-05
/// execution). ValidationPublishResponse.Shacl (DG.Grasshopper) references this type directly.
/// </summary>
public sealed class ShaclReportPayload
{
    public string Status { get; init; } = string.Empty;

    public bool? Conforms { get; init; }

    public ShaclCountsPayload? Counts { get; init; }

    public List<ShaclFindingPayload> Results { get; init; } = new();
}

public sealed class ShaclCountsPayload
{
    public int Violation { get; init; }

    public int Warning { get; init; }

    public int Info { get; init; }
}

public sealed class ShaclFindingPayload
{
    public string Severity { get; init; } = string.Empty;

    public string What { get; init; } = string.Empty;

    public string Where { get; init; } = string.Empty;

    public string HowToFix { get; init; } = string.Empty;

    public string FocusLabel { get; init; } = string.Empty;

    public string ShapeId { get; init; } = string.Empty;
}
