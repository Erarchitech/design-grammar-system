using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class ConnectorSessionClientTests
{
    private const string Password = "s3cret-Pa55word!";
    private const string Url = "http://localhost:8000";

    private sealed record Captured(
        HttpMethod Method,
        Uri? Uri,
        IReadOnlyDictionary<string, string> Headers,
        string Body);

    private sealed class RecordingHandler : HttpMessageHandler
    {
        private readonly Func<Captured, HttpResponseMessage>? _responder;
        private readonly Exception? _throw;

        public RecordingHandler(Func<Captured, HttpResponseMessage> responder)
        {
            _responder = responder;
        }

        public RecordingHandler(Exception toThrow)
        {
            _throw = toThrow;
        }

        public List<Captured> Requests { get; } = new();

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var h in request.Headers)
            {
                headers[h.Key] = string.Join(",", h.Value);
            }

            var body = request.Content is null
                ? string.Empty
                : await request.Content.ReadAsStringAsync(cancellationToken);
            var captured = new Captured(request.Method, request.RequestUri, headers, body);
            Requests.Add(captured);

            if (_throw is not null)
            {
                throw _throw;
            }

            return _responder!(captured);
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode code, string body) =>
        new(code) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private static HttpResponseMessage LoginOk()
    {
        var response = Json(HttpStatusCode.OK, "{\"username\":\"architect\"}");
        response.Headers.TryAddWithoutValidation("Set-Cookie", "dg_session=abc123; HttpOnly; Path=/; SameSite=Lax");
        return response;
    }

    private const string MintBody =
        "{\"token\":\"dgk_test\",\"project\":\"urban-tower\",\"connectorId\":\"grasshopper\"," +
        "\"username\":\"architect\",\"company\":\"acme\",\"expiresAt\":\"2026-10-12T20:00:00Z\"," +
        "\"expiresInSeconds\":28800," +
        "\"neo4j\":{\"uri\":\"bolt://localhost:7687\",\"user\":\"neo4j\",\"password\":\"graphpw\",\"database\":\"neo4j\"}}";

    /// <summary>Routes login/mint/logout by path; mint response is configurable.</summary>
    private static RecordingHandler Routed(Func<HttpResponseMessage> mint, Func<HttpResponseMessage>? login = null) =>
        new(req =>
        {
            var path = req.Uri!.AbsolutePath;
            if (path.EndsWith("/auth/login", StringComparison.Ordinal))
            {
                return (login ?? LoginOk)();
            }

            if (path.EndsWith("/auth/connector-session", StringComparison.Ordinal))
            {
                return mint();
            }

            return new HttpResponseMessage(HttpStatusCode.NoContent);
        });

    private static RecordingHandler HappyHandler() =>
        Routed(() => Json(HttpStatusCode.Created, MintBody));

    [Fact]
    public async Task SignIn_HappyPath_SendsLoginMintLogoutInOrderAndReturnsSession()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "urban-tower");

        Assert.Equal(ConnectorSessionOutcome.SignedIn, result.Outcome);
        Assert.Equal("dgk_test", result.SessionToken);
        Assert.Equal("urban-tower", result.Project);
        Assert.Equal(new DateTimeOffset(2026, 10, 12, 20, 0, 0, TimeSpan.Zero), result.ExpiresAt);
        Assert.NotNull(result.Bundle);
        Assert.Equal("bolt://localhost:7687", result.Bundle!.Value.Uri);
        Assert.Equal("graphpw", result.Bundle.Value.Password);
        Assert.Equal("urban-tower", result.Bundle.Value.Project);

        Assert.Equal(3, handler.Requests.Count);
        Assert.EndsWith("/auth/login", handler.Requests[0].Uri!.AbsolutePath);
        Assert.EndsWith("/auth/connector-session", handler.Requests[1].Uri!.AbsolutePath);
        Assert.EndsWith("/auth/logout", handler.Requests[2].Uri!.AbsolutePath);
        Assert.All(handler.Requests, r => Assert.Equal(HttpMethod.Post, r.Method));
    }

    [Fact]
    public async Task SignIn_MintRequest_CarriesCapturedCookieCsrfHeaderAndBody()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        await client.SignInAsync(Url, "architect", Password, "urban-tower", "grasshopper");

        var mint = handler.Requests[1];
        Assert.Equal("dg_session=abc123", mint.Headers["Cookie"]);
        Assert.Equal("1", mint.Headers["X-DG-CSRF"]);
        using var doc = JsonDocument.Parse(mint.Body);
        Assert.Equal("urban-tower", doc.RootElement.GetProperty("project").GetString());
        Assert.Equal("grasshopper", doc.RootElement.GetProperty("connector_id").GetString());

        // login and logout carry the CSRF header too; logout replays the cookie.
        Assert.Equal("1", handler.Requests[0].Headers["X-DG-CSRF"]);
        Assert.Equal("1", handler.Requests[2].Headers["X-DG-CSRF"]);
        Assert.Equal("dg_session=abc123", handler.Requests[2].Headers["Cookie"]);
    }

    [Fact]
    public async Task SignIn_LoginBody_CarriesUsernameAndPassword()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        await client.SignInAsync(Url, "architect", Password, null);

        using var doc = JsonDocument.Parse(handler.Requests[0].Body);
        Assert.Equal("architect", doc.RootElement.GetProperty("username").GetString());
        Assert.Equal(Password, doc.RootElement.GetProperty("password").GetString());
    }

    [Fact]
    public async Task SignIn_BlankProject_IsSentAsJsonNull()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        await client.SignInAsync(Url, "architect", Password, "  ");

        using var doc = JsonDocument.Parse(handler.Requests[1].Body);
        Assert.Equal(JsonValueKind.Null, doc.RootElement.GetProperty("project").ValueKind);
    }

    [Fact]
    public async Task SignIn_PasswordAppearsOnlyInLoginBody()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        await client.SignInAsync(Url, "architect", Password, "urban-tower");

        Assert.Contains(Password, handler.Requests[0].Body);
        foreach (var request in handler.Requests.Skip(1))
        {
            Assert.DoesNotContain(Password, request.Body);
        }

        foreach (var request in handler.Requests)
        {
            Assert.DoesNotContain(Password, request.Uri!.ToString());
            foreach (var header in request.Headers)
            {
                Assert.DoesNotContain(Password, header.Value);
            }
        }
    }

    [Fact]
    public async Task SignIn_RemoteHttp_ReturnsInsecureTransportWithZeroRequests()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync("http://dg.example.com:8000", "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.InsecureTransport, result.Outcome);
        Assert.Empty(handler.Requests);
    }

    [Theory]
    [InlineData("http://localhost:8000")]
    [InlineData("http://127.0.0.1:8000")]
    [InlineData("https://dg.example.com")]
    public async Task SignIn_LoopbackHttpAndRemoteHttps_Proceed(string url)
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.SignedIn, result.Outcome);
        Assert.Equal(3, handler.Requests.Count);
    }

    [Theory]
    [InlineData("", "pw")]
    [InlineData("   ", "pw")]
    [InlineData("architect", "")]
    public async Task SignIn_BlankUsernameOrPassword_ReturnsNotAttemptedWithZeroRequests(string user, string pw)
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, user, pw, "p");

        Assert.Equal(ConnectorSessionOutcome.NotAttempted, result.Outcome);
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task SignIn_Login401_ReturnsRejectedAfterOneRequest()
    {
        var handler = Routed(
            () => Json(HttpStatusCode.Created, MintBody),
            () => Json(HttpStatusCode.Unauthorized, "{\"error\":\"invalid credentials\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Rejected, result.Outcome);
        Assert.Single(handler.Requests);
        Assert.Null(result.SessionToken);
    }

    [Fact]
    public async Task SignIn_Login429_ReturnsThrottled()
    {
        var handler = Routed(
            () => Json(HttpStatusCode.Created, MintBody),
            () => Json(HttpStatusCode.TooManyRequests, "{\"error\":\"slow down\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Throttled, result.Outcome);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task SignIn_Mint403_ReturnsForbiddenWithServerCodeAndStillLogsOut()
    {
        var handler = Routed(() => Json(
            HttpStatusCode.Forbidden,
            "{\"error\":\"no access\",\"hint\":\"ask an owner\",\"code\":\"CONNECTOR_ACCESS_REQUIRED\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Forbidden, result.Outcome);
        Assert.Equal("CONNECTOR_ACCESS_REQUIRED", result.ServerCode);
        Assert.Null(result.SessionToken);
        Assert.Equal(3, handler.Requests.Count);
        Assert.EndsWith("/auth/logout", handler.Requests[2].Uri!.AbsolutePath);
    }

    [Fact]
    public async Task SignIn_Mint403ProjectForbidden_CarriesProjectForbiddenCode()
    {
        var handler = Routed(() => Json(
            HttpStatusCode.Forbidden,
            "{\"error\":\"no\",\"code\":\"PROJECT_FORBIDDEN\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Forbidden, result.Outcome);
        Assert.Equal("PROJECT_FORBIDDEN", result.ServerCode);
    }

    [Fact]
    public async Task SignIn_Mint422_ReturnsProjectRequiredWithHint()
    {
        var handler = Routed(() => Json(
            HttpStatusCode.UnprocessableEntity,
            "{\"error\":\"project required\",\"hint\":\"Eligible projects: alpha, beta\",\"code\":\"PROJECT_REQUIRED\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, null);

        Assert.Equal(ConnectorSessionOutcome.ProjectRequired, result.Outcome);
        Assert.Equal("PROJECT_REQUIRED", result.ServerCode);
        Assert.Contains("Eligible projects: alpha, beta", result.ServerMessage);
    }

    [Fact]
    public async Task SignIn_Mint500_ReturnsUnreachable()
    {
        var handler = Routed(() => new HttpResponseMessage(HttpStatusCode.InternalServerError));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Unreachable, result.Outcome);
    }

    [Fact]
    public async Task SignIn_Mint201WithoutDgkToken_ReturnsUnreachable()
    {
        var handler = Routed(() => Json(HttpStatusCode.Created, "{\"token\":\"dgc_old\",\"project\":\"p\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Unreachable, result.Outcome);
        Assert.Null(result.SessionToken);
    }

    [Fact]
    public async Task SignIn_LoginWithoutSessionCookie_ReturnsUnreachable()
    {
        var handler = Routed(
            () => Json(HttpStatusCode.Created, MintBody),
            () => Json(HttpStatusCode.OK, "{}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Unreachable, result.Outcome);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task SignIn_NetworkException_ReturnsUnreachableWithoutLeakingPassword()
    {
        var handler = new RecordingHandler(new HttpRequestException("connection refused"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Unreachable, result.Outcome);
        Assert.DoesNotContain(Password, result.ToString());
    }

    [Fact]
    public async Task SignIn_RequestTimeout_ReturnsUnreachable()
    {
        var handler = new RecordingHandler(new TaskCanceledException("timed out"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.Unreachable, result.Outcome);
    }

    [Fact]
    public async Task SignIn_CallerCancellation_Propagates()
    {
        var handler = new RecordingHandler(new TaskCanceledException("cancelled"));
        var client = new ConnectorSessionClient(handler);
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => client.SignInAsync(Url, "architect", Password, "p", cancellationToken: cts.Token));
    }

    [Fact]
    public async Task SignIn_LogoutFailure_IsSwallowed()
    {
        var handler = new RecordingHandler(req =>
        {
            var path = req.Uri!.AbsolutePath;
            if (path.EndsWith("/auth/login", StringComparison.Ordinal))
            {
                return LoginOk();
            }

            if (path.EndsWith("/auth/connector-session", StringComparison.Ordinal))
            {
                return Json(HttpStatusCode.Created, MintBody);
            }

            throw new HttpRequestException("logout failed");
        });
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.Equal(ConnectorSessionOutcome.SignedIn, result.Outcome);
    }

    [Fact]
    public async Task SignIn_ResultToString_ContainsNeitherPasswordNorSessionToken()
    {
        var handler = HappyHandler();
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "urban-tower");
        var text = result.ToString();

        Assert.Equal(ConnectorSessionOutcome.SignedIn, result.Outcome);
        Assert.DoesNotContain(Password, text);
        Assert.DoesNotContain("dgk_test", text);
        Assert.DoesNotContain("graphpw", text);
        Assert.Contains("<redacted>", text);
        Assert.Contains("SignedIn", text);
    }

    [Fact]
    public async Task SignIn_ServerMessages_NeverContainPassword()
    {
        var handler = Routed(
            () => Json(HttpStatusCode.Created, MintBody),
            () => Json(HttpStatusCode.Unauthorized, "{\"error\":\"invalid credentials\"}"));
        var client = new ConnectorSessionClient(handler);

        var result = await client.SignInAsync(Url, "architect", Password, "p");

        Assert.DoesNotContain(Password, result.ToString());
        Assert.DoesNotContain(Password, result.ServerMessage ?? string.Empty);
    }
}
