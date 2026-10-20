using System.Globalization;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Data;

/// <summary>
/// Default <see cref="IConnectorSessionClient"/> (D-35): <c>POST /auth/login</c> →
/// <c>POST /auth/connector-session</c> (with the captured <c>dg_session</c> cookie and the
/// <c>X-DG-CSRF</c> header) → best-effort <c>POST /auth/logout</c>.
///
/// The password flows only into the login request body; the session token only into the
/// returned result and the Bearer header of <see cref="SignOutAsync"/>. Neither enters a
/// field, URI, log or exception message. No Grasshopper SDK dependency.
/// </summary>
public sealed class ConnectorSessionClient : IConnectorSessionClient
{
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(6);
    private const string SessionCookieName = "dg_session";
    private const string CsrfHeader = "X-DG-CSRF";

    private readonly HttpClient _httpClient;

    public ConnectorSessionClient(HttpMessageHandler? handler = null)
    {
        // Cookies are captured and replayed by hand: a Secure cookie issued over a loopback
        // http URL would otherwise be dropped by the cookie container (Pitfall 8).
        _httpClient = new HttpClient(handler ?? new HttpClientHandler { UseCookies = false });
    }

    public async Task<ConnectorSessionResult> SignInAsync(
        string dataServiceUrl,
        string username,
        string password,
        string? project,
        string connectorId = "grasshopper",
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(username) || string.IsNullOrEmpty(password))
        {
            return ConnectorSessionResult.NotAttempted;
        }

        var baseUrl = NormalizeUrl(dataServiceUrl);

        // Pitfall 7 / T-1308-04-01: never send the password over plain http to a remote host.
        if (DataServiceRequestAuth.IsInsecureRemoteTransport(baseUrl))
        {
            return new ConnectorSessionResult(ConnectorSessionOutcome.InsecureTransport);
        }

        string? sessionCookie = null;
        try
        {
            // Step 1 - account login.
            var loginBody = JsonSerializer.Serialize(new Dictionary<string, string?>
            {
                ["username"] = username.Trim(),
                ["password"] = password,
            });
            using (var login = BuildRequest(HttpMethod.Post, $"{baseUrl}/auth/login", loginBody))
            using (var loginResponse = await SendAsync(login, cancellationToken).ConfigureAwait(false))
            {
                if (loginResponse.StatusCode == HttpStatusCode.Unauthorized)
                {
                    return new ConnectorSessionResult(ConnectorSessionOutcome.Rejected);
                }

                if (loginResponse.StatusCode == (HttpStatusCode)429)
                {
                    return new ConnectorSessionResult(ConnectorSessionOutcome.Throttled);
                }

                if (!loginResponse.IsSuccessStatusCode)
                {
                    return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
                }

                sessionCookie = ReadSessionCookie(loginResponse);
            }

            if (sessionCookie is null)
            {
                // Authenticated but no session cookie - nothing to mint with.
                return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
            }

            // Step 2 - mint the connector session.
            var mintBody = JsonSerializer.Serialize(new Dictionary<string, string?>
            {
                ["project"] = string.IsNullOrWhiteSpace(project) ? null : project.Trim(),
                ["connector_id"] = string.IsNullOrWhiteSpace(connectorId) ? "grasshopper" : connectorId.Trim(),
            });
            using var mint = BuildRequest(HttpMethod.Post, $"{baseUrl}/auth/connector-session", mintBody);
            mint.Headers.TryAddWithoutValidation("Cookie", $"{SessionCookieName}={sessionCookie}");
            using var mintResponse = await SendAsync(mint, cancellationToken).ConfigureAwait(false);
            var responseText = await mintResponse.Content
                .ReadAsStringAsync(cancellationToken)
                .ConfigureAwait(false);

            return MapMintResponse(mintResponse.StatusCode, responseText);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            // Network failure, DNS error, timeout or malformed response. Deliberately
            // message-free: nothing from the request path may reach the caller.
            return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
        }
        finally
        {
            if (sessionCookie is not null)
            {
                await TryLogoutAsync(baseUrl, sessionCookie).ConfigureAwait(false);
            }
        }
    }

    public async Task<bool> SignOutAsync(
        string dataServiceUrl,
        string sessionToken,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(sessionToken)
            || !sessionToken.Trim().StartsWith(DataServiceRequestAuth.TokenPrefix, StringComparison.Ordinal))
        {
            return false;
        }

        var baseUrl = NormalizeUrl(dataServiceUrl);
        if (DataServiceRequestAuth.IsInsecureRemoteTransport(baseUrl))
        {
            // Do not put the bearer on an unencrypted remote path to end it either.
            return false;
        }

        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Delete, $"{baseUrl}/auth/connector-session");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", sessionToken.Trim());
            using var response = await SendAsync(request, cancellationToken).ConfigureAwait(false);
            return response.StatusCode == HttpStatusCode.NoContent;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            return false;
        }
    }

    private static ConnectorSessionResult MapMintResponse(HttpStatusCode status, string body)
    {
        if (status == HttpStatusCode.Created || status == HttpStatusCode.OK)
        {
            return ParseSignedIn(body);
        }

        var (code, message) = ReadError(body);
        switch (status)
        {
            case HttpStatusCode.Unauthorized:
                return new ConnectorSessionResult(ConnectorSessionOutcome.Rejected, ServerCode: code, ServerMessage: message);
            case HttpStatusCode.Forbidden:
                return new ConnectorSessionResult(ConnectorSessionOutcome.Forbidden, ServerCode: code, ServerMessage: message);
            case (HttpStatusCode)422:
                return new ConnectorSessionResult(ConnectorSessionOutcome.ProjectRequired, ServerCode: code, ServerMessage: message);
            case (HttpStatusCode)429:
                return new ConnectorSessionResult(ConnectorSessionOutcome.Throttled, ServerCode: code, ServerMessage: message);
            default:
                return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
        }
    }

    private static ConnectorSessionResult ParseSignedIn(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
            }

            var token = ReadString(root, "token");
            if (string.IsNullOrWhiteSpace(token)
                || !token.StartsWith(DataServiceRequestAuth.TokenPrefix, StringComparison.Ordinal))
            {
                return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
            }

            var project = ReadString(root, "project");
            DateTimeOffset? expiresAt = null;
            var expiresText = ReadString(root, "expiresAt");
            if (expiresText is not null
                && DateTimeOffset.TryParse(
                    expiresText,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal,
                    out var parsed))
            {
                expiresAt = parsed;
            }

            ConnectionBundle? bundle = null;
            if (root.TryGetProperty("neo4j", out var neo) && neo.ValueKind == JsonValueKind.Object)
            {
                bundle = new ConnectionBundle(
                    Uri: ReadString(neo, "uri"),
                    User: ReadString(neo, "user"),
                    Password: ReadString(neo, "password"),
                    Database: ReadString(neo, "database"),
                    Project: project);
            }

            return new ConnectorSessionResult(
                ConnectorSessionOutcome.SignedIn,
                Project: project,
                Bundle: bundle,
                SessionToken: token,
                ExpiresAt: expiresAt);
        }
        catch (JsonException)
        {
            return new ConnectorSessionResult(ConnectorSessionOutcome.Unreachable);
        }
    }

    private static (string? Code, string? Message) ReadError(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return (null, null);
            }

            var code = ReadString(root, "code");
            var hint = ReadString(root, "hint");
            var error = ReadString(root, "error");
            var message = !string.IsNullOrWhiteSpace(hint) ? hint : error;
            return (code, message);
        }
        catch (JsonException)
        {
            return (null, null);
        }
    }

    private static string? ReadString(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString()
            : null;

    private static string? ReadSessionCookie(HttpResponseMessage response)
    {
        if (!response.Headers.TryGetValues("Set-Cookie", out var values))
        {
            return null;
        }

        var prefix = SessionCookieName + "=";
        foreach (var header in values)
        {
            var firstPair = header.Split(';', 2)[0].Trim();
            if (firstPair.StartsWith(prefix, StringComparison.Ordinal))
            {
                var value = firstPair.Substring(prefix.Length);
                return value.Length > 0 ? value : null;
            }
        }

        return null;
    }

    private static HttpRequestMessage BuildRequest(HttpMethod method, string url, string jsonBody)
    {
        var request = new HttpRequestMessage(method, url)
        {
            Content = new StringContent(jsonBody, Encoding.UTF8, "application/json"),
        };
        request.Headers.TryAddWithoutValidation(CsrfHeader, "1");
        return request;
    }

    private Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
        _httpClient.SendAsync(request, cancellationToken).WaitAsync(RequestTimeout, cancellationToken);

    private async Task TryLogoutAsync(string baseUrl, string sessionCookie)
    {
        try
        {
            using var request = BuildRequest(HttpMethod.Post, $"{baseUrl}/auth/logout", "{}");
            request.Headers.TryAddWithoutValidation("Cookie", $"{SessionCookieName}={sessionCookie}");
            using var response = await SendAsync(request, CancellationToken.None).ConfigureAwait(false);
        }
        catch
        {
            // Best effort: the connector session is independent of the account session.
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
