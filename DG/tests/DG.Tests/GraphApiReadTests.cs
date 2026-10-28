using System.Net;
using System.Net.Sockets;
using System.Text;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

/// <summary>
/// Quick 261028-vm9: the repositories read through the data-service <c>/connector-graph</c> route when
/// the connection carries a <see cref="ConnectionInfo.GraphApiUrl"/>. A loopback HttpListener stands in
/// for the server, so the real HTTP path, the Bearer header and the row mapping are exercised end to end.
/// </summary>
public sealed class GraphApiReadTests : IDisposable
{
    private const string Token = "dgk_test-session-token";

    private readonly HttpListener _listener = new();
    private readonly string _baseUrl;
    private readonly Dictionary<string, string> _answers = new(StringComparer.Ordinal);
    private readonly List<(string Path, string Query, string? Authorization)> _requests = new();
    private readonly Task _loop;
    private HttpStatusCode _status = HttpStatusCode.OK;

    public GraphApiReadTests()
    {
        var probe = new TcpListener(IPAddress.Loopback, 0);
        probe.Start();
        var port = ((IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();

        _baseUrl = $"http://127.0.0.1:{port}";
        _listener.Prefixes.Add(_baseUrl + "/");
        _listener.Start();
        _loop = Task.Run(Serve);
    }

    public void Dispose()
    {
        _listener.Close();
        try
        {
            _loop.Wait(TimeSpan.FromSeconds(2));
        }
        catch (AggregateException)
        {
        }
    }

    private async Task Serve()
    {
        while (_listener.IsListening)
        {
            HttpListenerContext context;
            try
            {
                context = await _listener.GetContextAsync();
            }
            catch (Exception)
            {
                return;
            }

            var path = context.Request.Url!.AbsolutePath;
            lock (_requests)
            {
                _requests.Add((path, context.Request.Url.Query, context.Request.Headers["Authorization"]));
            }

            var queryId = path[(path.LastIndexOf('/') + 1)..];
            var body = _answers.TryGetValue(queryId, out var answer) ? answer : "{\"rows\":[]}";
            if (_status != HttpStatusCode.OK)
            {
                body = "{\"detail\":{\"code\":\"PROJECT_FORBIDDEN\"}}";
            }

            var bytes = Encoding.UTF8.GetBytes(body);
            context.Response.StatusCode = (int)_status;
            context.Response.ContentType = "application/json";
            await context.Response.OutputStream.WriteAsync(bytes);
            context.Response.Close();
        }
    }

    private ConnectionInfo Connection() => new()
    {
        Project = "Tenant Alpha",
        GraphApiUrl = _baseUrl,
        GraphApiToken = Token,
        IsConnected = true,
    };

    [Fact]
    public async Task Rules_AreAssembledFromServerRows_WithBearerAndEscapedProject()
    {
        _answers["rules"] = """
            {"rows":[{"id":"R_URB_HEIGHT_MAX_75_V","name":"Height","description":"Max 75 m","kind":"violation",
                      "text":"t","swrl":"","project":"Tenant Alpha","graph":"Metagraph"}]}
            """;
        _answers["atoms"] = """
            {"rows":[
              {"ruleId":"R_URB_HEIGHT_MAX_75_V","relationType":"HAS_BODY","atomOrder":1,"atomId":"A1","atomType":"ClassAtom",
               "predicateIri":"dg:Building","predicateLabel":"Building","argPos":1,"argLabels":["Var"],
               "varName":"b","litLex":null,"litDatatype":null},
              {"ruleId":"R_URB_HEIGHT_MAX_75_V","relationType":"HAS_BODY","atomOrder":2,"atomId":"A2","atomType":"BuiltinAtom",
               "predicateIri":null,"predicateLabel":null,"argPos":2,"argLabels":["Literal"],
               "varName":null,"litLex":"75","litDatatype":"xsd:decimal"},
              {"ruleId":"UNKNOWN","relationType":"HAS_HEAD","atomOrder":1,"atomId":"A9","atomType":"ClassAtom",
               "predicateIri":null,"predicateLabel":null,"argPos":0,"argLabels":null,
               "varName":null,"litLex":null,"litDatatype":null}
            ]}
            """;

        var rules = await new Neo4jRuleRepository().GetRulesAsync(Connection());

        var rule = Assert.Single(rules);
        Assert.Equal("R_URB_HEIGHT_MAX_75_V", rule.Id);
        Assert.Equal(2, rule.BodyAtoms.Count);
        Assert.Equal("dg:Building", rule.BodyAtoms[0].PredicateIri);
        Assert.Equal("b", Assert.Single(rule.BodyAtoms[0].Args).Value);
        var literal = Assert.Single(rule.BodyAtoms[1].Args);
        Assert.Equal("75", literal.Value);
        Assert.Equal("xsd:decimal", literal.Datatype);

        lock (_requests)
        {
            Assert.Contains(_requests, r => r.Path == "/connector-graph/Tenant%20Alpha/rules");
            Assert.Contains(_requests, r => r.Path == "/connector-graph/Tenant%20Alpha/atoms");
            Assert.All(_requests, r => Assert.Equal($"Bearer {Token}", r.Authorization));
        }
    }

    [Fact]
    public async Task OntologyReads_UseTheirNamedQueries()
    {
        _answers["classes"] = """{"rows":[{"iri":"dg:Building","label":"Building"}]}""";
        _answers["objProperties"] = """{"rows":[{"iri":"dg:hosts","label":"hosts"}]}""";
        _answers["dataProperties"] = """{"rows":[{"iri":"dg:height","label":"height"}]}""";
        var repository = new Neo4jOntoGraphRepository();

        var classes = await repository.GetClassesAsync(Connection());
        var objProperties = await repository.GetObjPropertiesAsync(Connection());
        var dataProperties = await repository.GetDataPropertiesAsync(Connection());

        Assert.Equal("Building", Assert.Single(classes).Label);
        Assert.Equal("hosts", Assert.Single(objProperties).Label);
        Assert.Equal("dg:height", Assert.Single(dataProperties).Iri);
    }

    [Fact]
    public async Task Evidence_SendsTheRunIdAsAQueryParameter()
    {
        _answers["evidence"] = """{"rows":[{"evidenceEnvelopeJson":null}]}""";

        var result = await new Neo4jValidGraphRepository().GetPerObjectVerdictsAsync(Connection(), "RUN 1&x=2");

        Assert.False(result.EnvelopePresent);
        lock (_requests)
        {
            var request = Assert.Single(_requests);
            Assert.Equal("/connector-graph/Tenant%20Alpha/evidence", request.Path);
            Assert.Equal("?runId=RUN%201%26x%3D2", request.Query);
        }
    }

    [Fact]
    public async Task Runs_DegradeWhenTheStandaloneStatesReadFails_ButNotWhenTheRunsReadFails()
    {
        _answers["runs"] = """
            {"rows":[{"runId":"RUN_1","project":"Tenant Alpha","createdAt":"2026-10-28T10:00:00Z",
                      "rulesJson":"[{\"ruleId\":\"R1\",\"passed\":true}]","statePayloadJson":null}]}
            """;

        var result = await new Neo4jValidGraphRepository().GetRunsAsync(Connection());

        var run = Assert.Single(result.Runs);
        Assert.Equal("RUN_1", run.RunId);
        Assert.Equal(new[] { "R1" }, run.RuleIds);

        _status = HttpStatusCode.Forbidden;
        var failure = await Assert.ThrowsAsync<GraphApiException>(
            () => new Neo4jValidGraphRepository().GetRunsAsync(Connection()));
        Assert.Contains("PROJECT_FORBIDDEN", failure.Message);
        Assert.DoesNotContain(Token, failure.Message);
        Assert.DoesNotContain(_baseUrl, failure.Message);
    }

    [Fact]
    public async Task ServerMode_ProbeReportsConnected_AndFailureWithoutTheToken()
    {
        var service = new Neo4jConnectorService();

        var ok = await service.TryConnectAsync(Connection());
        Assert.True(ok.IsConnected);
        Assert.Equal(_baseUrl, ok.GraphApiUrl);
        Assert.Equal(Token, ok.GraphApiToken);

        _status = HttpStatusCode.Unauthorized;
        var failed = await service.TryConnectAsync(Connection());
        Assert.False(failed.IsConnected);
        Assert.DoesNotContain(Token, failed.StatusMessage);
    }

    [Fact]
    public async Task PlainHttpToARemoteHost_IsRefusedBeforeAnyRequest()
    {
        var remote = new ConnectionInfo { Project = "P", GraphApiUrl = "http://dg.example.com", GraphApiToken = Token };

        var failure = await Assert.ThrowsAsync<GraphApiException>(() => new Neo4jOntoGraphRepository().GetClassesAsync(remote));

        Assert.Contains("https", failure.Message);
    }

    [Fact]
    public async Task MissingToken_IsReportedWithoutARequest()
    {
        var connection = new ConnectionInfo { Project = "P", GraphApiUrl = _baseUrl, GraphApiToken = null };

        await Assert.ThrowsAsync<GraphApiException>(() => new Neo4jOntoGraphRepository().GetClassesAsync(connection));

        lock (_requests)
        {
            Assert.Empty(_requests);
        }
    }

    [Theory]
    [InlineData(null, "http://localhost:8000")]
    [InlineData("", "http://localhost:8000")]
    [InlineData("   ", "http://localhost:8000")]
    [InlineData("dg.example.com", "https://dg.example.com")]
    [InlineData(" https://dg.example.com/ ", "https://dg.example.com")]
    [InlineData("http://localhost:8080", "http://localhost:8080")]
    public void NormalizeServerUrl_FillsDefaultsAndTrims(string? typed, string expected)
    {
        Assert.Equal(expected, DataServiceRequestAuth.NormalizeServerUrl(typed));
    }

    [Theory]
    [InlineData("http://localhost:8000", false)]
    [InlineData("http://127.0.0.1:8000", false)]
    [InlineData("https://dg.example.com", true)]
    [InlineData("", false)]
    public void IsRemoteServer_OnlyForNonLoopbackHosts(string url, bool expected)
    {
        Assert.Equal(expected, DataServiceRequestAuth.IsRemoteServer(url));
    }
}
