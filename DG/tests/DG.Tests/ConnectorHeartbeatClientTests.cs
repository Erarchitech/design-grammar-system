using System.Net;
using System.Net.Http;
using System.Text;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class ConnectorHeartbeatClientTests
{
    private sealed class StubHttpMessageHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage>? _responder;
        private readonly Exception? _throw;

        public StubHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> responder)
        {
            _responder = responder;
        }

        public StubHttpMessageHandler(Exception toThrow)
        {
            _throw = toThrow;
        }

        public int CallCount { get; private set; }

        public HttpRequestMessage? LastRequest { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            CallCount++;
            LastRequest = request;
            if (_throw is not null)
            {
                throw _throw;
            }

            return Task.FromResult(_responder!(request));
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode code, string body) =>
        new(code) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    [Fact]
    public async Task Check_Http200_ReturnsAuthenticatedWithStatusAndBearerHeader()
    {
        var handler = new StubHttpMessageHandler(
            _ => Json(HttpStatusCode.OK, "{\"connector_id\":\"grasshopper\",\"status\":\"active\"}"));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_validtoken123");

        Assert.Equal(HeartbeatOutcome.Authenticated, result.Outcome);
        Assert.Equal("active", result.Status);
        Assert.Equal(1, handler.CallCount);
        Assert.NotNull(handler.LastRequest);
        Assert.Equal("Bearer", handler.LastRequest!.Headers.Authorization?.Scheme);
        Assert.Equal("dgc_validtoken123", handler.LastRequest.Headers.Authorization?.Parameter);
        Assert.EndsWith("/connectors/heartbeat", handler.LastRequest.RequestUri?.AbsolutePath);
    }

    [Fact]
    public async Task Check_Http200_WithNeo4jBundle_PopulatesBundle()
    {
        // Phase 825: an authenticated heartbeat returns the project + host-facing
        // Neo4j connection bundle the token unlocks.
        const string body =
            "{\"connector_id\":\"grasshopper\",\"status\":\"active\",\"project\":\"urban-tower\"," +
            "\"neo4j\":{\"uri\":\"bolt://localhost:7687\",\"user\":\"neo4j\"," +
            "\"password\":\"12345678\",\"database\":\"neo4j\"}}";
        var handler = new StubHttpMessageHandler(_ => Json(HttpStatusCode.OK, body));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_valid");

        Assert.Equal(HeartbeatOutcome.Authenticated, result.Outcome);
        Assert.Equal("active", result.Status);
        Assert.NotNull(result.Bundle);
        var bundle = result.Bundle!.Value;
        Assert.Equal("bolt://localhost:7687", bundle.Uri);
        Assert.Equal("neo4j", bundle.User);
        Assert.Equal("12345678", bundle.Password);
        Assert.Equal("neo4j", bundle.Database);
        Assert.Equal("urban-tower", bundle.Project);
    }

    [Fact]
    public async Task Check_Http200_StatusOnlyBody_LeavesBundleNull()
    {
        // Back-compat: a pre-825 status-only body still authenticates with no bundle.
        var handler = new StubHttpMessageHandler(
            _ => Json(HttpStatusCode.OK, "{\"connector_id\":\"grasshopper\",\"status\":\"active\"}"));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_valid");

        Assert.Equal(HeartbeatOutcome.Authenticated, result.Outcome);
        Assert.Null(result.Bundle);
    }

    [Fact]
    public async Task Check_Http401_ReturnsRejected()
    {
        var handler = new StubHttpMessageHandler(
            _ => Json(HttpStatusCode.Unauthorized, "{\"error\":\"nope\"}"));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_revoked");

        Assert.Equal(HeartbeatOutcome.Rejected, result.Outcome);
    }

    [Fact]
    public async Task Check_Http500_ReturnsUnreachable()
    {
        var handler = new StubHttpMessageHandler(
            _ => new HttpResponseMessage(HttpStatusCode.InternalServerError));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_whatever");

        Assert.Equal(HeartbeatOutcome.Unreachable, result.Outcome);
    }

    [Fact]
    public async Task Check_NetworkException_ReturnsUnreachable()
    {
        var handler = new StubHttpMessageHandler(new HttpRequestException("connection refused"));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "dgc_whatever");

        Assert.Equal(HeartbeatOutcome.Unreachable, result.Outcome);
    }

    [Fact]
    public async Task Check_NonDgcToken_ReturnsRejectedWithoutNetworkCall()
    {
        var handler = new StubHttpMessageHandler(_ => new HttpResponseMessage(HttpStatusCode.OK));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "not-a-real-token");

        Assert.Equal(HeartbeatOutcome.Rejected, result.Outcome);
        Assert.Equal(0, handler.CallCount);
    }

    [Fact]
    public async Task Check_EmptyToken_ReturnsNotAttemptedWithoutNetworkCall()
    {
        var handler = new StubHttpMessageHandler(_ => new HttpResponseMessage(HttpStatusCode.OK));
        var client = new ConnectorHeartbeatClient(handler);

        var result = await client.CheckAsync("http://localhost:8000", "   ");

        Assert.Equal(HeartbeatOutcome.NotAttempted, result.Outcome);
        Assert.Equal(0, handler.CallCount);
    }
}
