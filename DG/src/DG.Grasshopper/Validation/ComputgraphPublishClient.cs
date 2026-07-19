#if GRASSHOPPER_SDK
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;

namespace DG.Grasshopper.Validation;

internal static class ComputgraphPublishClient
{
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

    public static ComputgraphPublishResponse Publish(string cgContextJson, string project, string dataServiceUrl)
    {
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/computgraph/publish";
        var request = new ComputgraphPublishRequest
        {
            Project = project,
            CgContext = JsonSerializer.Deserialize<JsonElement>(cgContextJson),
        };

        HttpResponseMessage response;
        try
        {
            response = HttpClient.PostAsJsonAsync(endpoint, request, JsonOptions).GetAwaiter().GetResult();
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
                throw new InvalidOperationException($"Computgraph publish failed ({(int)response.StatusCode}): {body}");
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
