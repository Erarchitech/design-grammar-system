#if GRASSHOPPER_SDK
using System.Text.Json;

namespace DG.Grasshopper.Validation;

internal sealed class ComputgraphPublishRequest
{
    public string Project { get; init; } = "default-project";

    /// <summary>
    /// The cgContextJson v1 envelope carrying dgId-stamped entities.
    /// Deserialized from the serialized string by ComputgraphPublishClient before POST.
    /// </summary>
    public JsonElement CgContext { get; init; }
}

internal sealed class ComputgraphPublishResponse
{
    public string Status { get; init; } = string.Empty;

    /// <summary>
    /// Entity ids that were present on the server for this definition but absent
    /// from the published payload. Never auto-deleted (CONTEXT.md "stale-entity
    /// cleanup is reported, deletion is explicit").
    /// </summary>
    public List<string> StaleEntityIds { get; init; } = new();
}
#else
namespace DG.Grasshopper.Validation;

internal sealed class ComputgraphPublishRequest
{
}

internal sealed class ComputgraphPublishResponse
{
}
#endif
