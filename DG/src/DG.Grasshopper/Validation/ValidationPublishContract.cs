#if GRASSHOPPER_SDK
namespace DG.Grasshopper.Validation;

internal sealed class ValidationPublishRequest
{
    public string Project { get; init; } = "default-project";

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
}
#else
namespace DG.Grasshopper.Validation;

internal sealed class ValidationPublishRequest
{
}
#endif
