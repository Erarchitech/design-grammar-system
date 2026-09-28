#if GRASSHOPPER_SDK
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using DG.Core.Data;
using DG.Core.Services;

namespace DG.Grasshopper.Validation;

internal static class ComputgraphPublishClient
{
    // Named per D-04's Artifacts table; used only in error-template text, never in a header.
    private const string ComponentName = "COMPUTGRAPH PUBLISH";

    // Bounded timeout (Phase 36 WR-09): Publish runs synchronously on the GH
    // solver thread (.GetAwaiter().GetResult()); the default 100s HttpClient
    // timeout would freeze Rhino's UI for up to 100s if data-service accepts
    // the TCP connection but stalls (container restarting, Neo4j blocked
    // mid-transaction).
    private static readonly HttpClient HttpClient = new() { Timeout = TimeSpan.FromSeconds(15) };
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public static ComputgraphPublishResponse Publish(string cgContextJson, string project, string dataServiceUrl, string? token)
    {
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/computgraph/publish";
        var request = new ComputgraphPublishRequest
        {
            Project = project,
            CgContext = JsonSerializer.Deserialize<JsonElement>(cgContextJson),
        };

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = JsonContent.Create(request, options: JsonOptions),
        };

        // D-04/Correction 5: bail out before any network I/O when the token is
        // missing or malformed. The token itself never enters an exception message.
        if (!DataServiceRequestAuth.TryApplyConnectorToken(httpRequest, token, out _))
        {
            throw new InvalidOperationException(ErrorMessageTemplates.PublishTokenMissing(ComponentName));
        }

        HttpResponseMessage response;
        try
        {
            response = HttpClient.SendAsync(httpRequest).GetAwaiter().GetResult();
        }
        catch (TaskCanceledException)
        {
            throw new InvalidOperationException("Computgraph publish failed: data-service did not respond within 15s.");
        }

        using (response)
        {
            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();

            if (!response.IsSuccessStatusCode)
            {
                var outcome = DataServiceRequestAuth.ClassifyStatus(response.StatusCode);
                var message = outcome switch
                {
                    PublishAuthOutcome.Rejected => ErrorMessageTemplates.PublishTokenRejected(ComponentName),
                    PublishAuthOutcome.Forbidden => ErrorMessageTemplates.PublishProjectForbidden(ComponentName),
                    _ => $"Computgraph publish failed ({(int)response.StatusCode}): {body}",
                };
                throw new InvalidOperationException(message);
            }

            var parsed = JsonSerializer.Deserialize<ComputgraphPublishResponse>(body, JsonOptions);
            if (parsed is null)
            {
                throw new InvalidOperationException("Computgraph publish failed: backend returned an empty response.");
            }

            return parsed;
        }
    }

    private static string NormalizeUrl(string dataServiceUrl)
    {
        var normalized = string.IsNullOrWhiteSpace(dataServiceUrl)
            ? "http://localhost:8000"
            : dataServiceUrl.Trim();
        return normalized.TrimEnd('/');
    }
}
#else
namespace DG.Grasshopper.Validation;

internal static class ComputgraphPublishClient
{
}
#endif
