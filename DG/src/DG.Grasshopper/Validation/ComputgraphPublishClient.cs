#if GRASSHOPPER_SDK
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;

namespace DG.Grasshopper.Validation;

internal static class ComputgraphPublishClient
{
    private static readonly HttpClient HttpClient = new();
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

        using var response = HttpClient.PostAsJsonAsync(endpoint, request, JsonOptions).GetAwaiter().GetResult();
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
