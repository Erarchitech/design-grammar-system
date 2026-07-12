#if GRASSHOPPER_SDK
using DG.Core.Validation;

namespace DG.Grasshopper.Validation;

internal sealed class ValidationPublishRequest
{
    public string Project { get; init; } = "default-project";

    /// <summary>
    /// Serialized ParamState JSON from the PARAMETER STATE component.
    /// Null when no state was captured for this validation run.
    /// </summary>
    public string? StatePayloadJson { get; init; }

    /// <summary>
    /// Per-ObjState Boolean list from the VALIDATOR component (Phase 18 GHVL-05).
    /// Index-matched to DesignState.ObjStates order. Null for pre-v7.0 clients.
    /// </summary>
    public List<bool>? ValidStatus { get; set; }

    public List<ValidationPublishRulePayload> Rules { get; } = new();

    public List<ValidationPublishRuleResultPayload> RuleResults { get; } = new();

    public List<ValidationPublishEntityPayload> Entities { get; } = new();
}

internal sealed class ValidationPublishRulePayload
{
    public string RuleId { get; init; } = string.Empty;

    public string RuleName { get; init; } = string.Empty;

    public string RuleDescription { get; init; } = string.Empty;
}

internal sealed class ValidationPublishRuleResultPayload
{
    public string RuleId { get; init; } = string.Empty;

    public bool Passed { get; init; }

    public List<string> FailedEntityIds { get; } = new();

    public List<string> PassedEntityIds { get; } = new();
}

internal sealed class ValidationPublishEntityPayload
{
    public string DgEntityId { get; init; } = string.Empty;

    public string? DisplayName { get; init; }

    public ValidationGeometryPayload? Geometry { get; init; }

    public List<string> RuleIds { get; } = new();

    public List<string> FailedRuleIds { get; } = new();

    public List<string> PassedRuleIds { get; } = new();

    public string OverallStatus { get; init; } = "unknown";
}

internal sealed class ValidationGeometryPayload
{
    public string Units { get; init; } = "meters";

    public List<ValidationGeometryItemPayload> Items { get; } = new();
}

internal sealed class ValidationGeometryItemPayload
{
    public string Kind { get; init; } = string.Empty;

    public List<double> Vertices { get; } = new();

    public List<List<int>> Faces { get; } = new();

    public List<int> Colors { get; } = new();

    public List<double> Values { get; } = new();
}

internal sealed class ValidationPublishResponse
{
    public string Status { get; init; } = string.Empty;

    public string RunId { get; init; } = string.Empty;

    public string ValidationModelId { get; init; } = string.Empty;

    public string ValidationVersionId { get; init; } = string.Empty;

    public string BaseVersionId { get; init; } = string.Empty;

    public string ModelViewerUrl { get; init; } = string.Empty;

    /// <summary>
    /// SHACL report block (Phase 823, D-15). Null for pre-823 servers, unavailable/timeout
    /// sidecars, or malformed data-service responses -- ValidatorComponent must treat a null
    /// Shacl as "not checked", never as a failure.
    /// </summary>
    public ShaclReportPayload? Shacl { get; init; }
}
#else
namespace DG.Grasshopper.Validation;

internal sealed class ValidationPublishRequest
{
}
#endif
