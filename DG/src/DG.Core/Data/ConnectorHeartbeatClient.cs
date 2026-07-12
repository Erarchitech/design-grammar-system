using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Data;

/// <summary>
/// Default <see cref="IConnectorHeartbeatClient"/>. Posts a Bearer-authenticated
/// heartbeat to data-service and maps the HTTP result to a <see cref="HeartbeatResult"/>.
/// The token flows only into the Authorization header — never into a field, log,
/// exception message, or the returned result.
/// </summary>
public sealed class ConnectorHeartbeatClient : IConnectorHeartbeatClient
{
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(6);
    private const string TokenPrefix = "dgc_";

    private readonly HttpClient _httpClient;

    public ConnectorHeartbeatClient(HttpMessageHandler? handler = null)
    {
        _httpClient = handler is null ? new HttpClient() : new HttpClient(handler);
    }

    public async Task<HeartbeatResult> CheckAsync(
        string dataServiceUrl,
        string token,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(token))
        {
            return HeartbeatResult.NotAttempted;
        }

        if (!token.StartsWith(TokenPrefix, StringComparison.Ordinal))
        {
            // Not a platform-token shape — reject without a network round-trip.
            return new HeartbeatResult(HeartbeatOutcome.Rejected, null);
        }

        try
        {
            using var request = new HttpRequestMessage(
                HttpMethod.Post,
                $"{NormalizeUrl(dataServiceUrl)}/connectors/heartbeat");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

            using var response = await _httpClient
                .SendAsync(request, cancellationToken)
                .WaitAsync(RequestTimeout, cancellationToken)
                .ConfigureAwait(false);

            if (response.StatusCode == HttpStatusCode.OK)
            {
                var body = await response.Content
                    .ReadAsStringAsync(cancellationToken)
                    .ConfigureAwait(false);
                return new HeartbeatResult(HeartbeatOutcome.Authenticated, TryReadStatus(body));
            }

            if (response.StatusCode == HttpStatusCode.Unauthorized)
            {
                return new HeartbeatResult(HeartbeatOutcome.Rejected, null);
            }

            // Any other status (5xx, unexpected) is treated as a transient reachability problem.
            return new HeartbeatResult(HeartbeatOutcome.Unreachable, null);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Caller cancelled (e.g. component removed / re-solve) — propagate.
            throw;
        }
        catch
        {
            // Network failure, DNS error, request timeout, or malformed response.
            return new HeartbeatResult(HeartbeatOutcome.Unreachable, null);
        }
    }

    private static string? TryReadStatus(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.ValueKind == JsonValueKind.Object
                && doc.RootElement.TryGetProperty("status", out var status)
                && status.ValueKind == JsonValueKind.String)
            {
                return status.GetString();
            }
        }
        catch (JsonException)
        {
            // Tolerate a non-JSON / unexpected body — the 200 still authenticated.
        }

        return null;
    }

    private static string NormalizeUrl(string dataServiceUrl)
    {
        var normalized = string.IsNullOrWhiteSpace(dataServiceUrl)
            ? "http://localhost:8000"
            : dataServiceUrl.Trim();
        return normalized.TrimEnd('/');
    }
}
