using System.Text;
using System.Text.Json;

namespace DG.Core.Bridge;

/// <summary>
/// Parses/emits the DG Canvas Bridge wire protocol: raw TCP, UTF-8,
/// newline-terminated, one JSON object per line, no BOM.
///
/// Request line (client -&gt; listener): {"type":"&lt;command&gt;","parameters":{ ... }}
/// Response line (listener -&gt; client), always single-line, always carries the
/// handshake fields bridge="dg", version=1:
///   Success: {"bridge":"dg","version":1,"status":"ok","result":&lt;payload&gt;}
///   Error:   {"bridge":"dg","version":1,"status":"error","error":{"message":"...","code":"..."}}
/// </summary>
public static class CanvasBridgeProtocol
{
    public const string BridgeName = "dg";
    public const int Version = 1;

    /// <summary>Guard against unbounded memory use from a malformed/oversized request line.</summary>
    public const int MaxRequestBytes = 5 * 1024 * 1024;

    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    /// <summary>
    /// Parses a single wire-protocol request line. Returns false (never throws)
    /// for null/whitespace/oversized/unparseable input. Strips a single leading
    /// UTF-8 BOM (U+FEFF) before parsing.
    /// </summary>
    public static bool TryParse(string? line, out CanvasCommandRequest request)
    {
        request = null!;

        if (string.IsNullOrWhiteSpace(line))
        {
            return false;
        }

        if (Encoding.UTF8.GetByteCount(line) > MaxRequestBytes)
        {
            return false;
        }

        if (line.Length > 0 && line[0] == '\uFEFF')
        {
            line = line[1..];
        }

        try
        {
            var dto = JsonSerializer.Deserialize<CanvasCommandRequestDto>(line, Options);
            if (dto is null || string.IsNullOrEmpty(dto.Type))
            {
                return false;
            }

            request = new CanvasCommandRequest(dto.Type, dto.Parameters);
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    /// <summary>Builds a single-line success envelope carrying the handshake fields.</summary>
    public static string BuildOk(object? result)
    {
        var envelope = new BridgeOkEnvelope
        {
            Bridge = BridgeName,
            Version = Version,
            Status = "ok",
            Result = result,
        };

        return JsonSerializer.Serialize(envelope, Options);
    }

    /// <summary>Builds a single-line error envelope carrying the handshake fields.</summary>
    public static string BuildError(string message, string code)
    {
        var envelope = new BridgeErrorEnvelope
        {
            Bridge = BridgeName,
            Version = Version,
            Status = "error",
            Error = new BridgeErrorDetail { Message = message, Code = code },
        };

        return JsonSerializer.Serialize(envelope, Options);
    }

    private sealed class CanvasCommandRequestDto
    {
        public string? Type { get; init; }

        public JsonElement Parameters { get; init; }
    }

    private sealed class BridgeOkEnvelope
    {
        public string Bridge { get; init; } = string.Empty;

        public int Version { get; init; }

        public string Status { get; init; } = string.Empty;

        public object? Result { get; init; }
    }

    private sealed class BridgeErrorEnvelope
    {
        public string Bridge { get; init; } = string.Empty;

        public int Version { get; init; }

        public string Status { get; init; } = string.Empty;

        public BridgeErrorDetail Error { get; init; } = null!;
    }

    private sealed class BridgeErrorDetail
    {
        public string Message { get; init; } = string.Empty;

        public string Code { get; init; } = string.Empty;
    }
}
