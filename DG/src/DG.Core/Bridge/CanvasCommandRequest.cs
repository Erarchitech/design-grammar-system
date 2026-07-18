using System.Text.Json;

namespace DG.Core.Bridge;

/// <summary>
/// A parsed request line from the DG Canvas Bridge wire protocol:
/// {"type":"&lt;command&gt;","parameters":{ ... }}
/// </summary>
public sealed record CanvasCommandRequest(string Type, JsonElement Parameters)
{
    /// <summary>
    /// Reads a string property from <see cref="Parameters"/>. Returns an empty
    /// string when the property is absent, not a string, or Parameters is not
    /// an object (never throws).
    /// </summary>
    public string TryGetString(string key)
    {
        if (Parameters.ValueKind != JsonValueKind.Object)
        {
            return string.Empty;
        }

        if (!Parameters.TryGetProperty(key, out var value))
        {
            return string.Empty;
        }

        return value.ValueKind == JsonValueKind.String ? value.GetString() ?? string.Empty : string.Empty;
    }
}
