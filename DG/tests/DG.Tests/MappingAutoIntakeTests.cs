using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using DG.Core.Mapping;

namespace DG.Tests;

/// <summary>
/// Phase 1303, owner amendment 2026-10-18: CONNECTOR proposes the mapping automatically —
/// canvas text (groups, scribbles, component names) and named sliders take part.
/// </summary>
public sealed class MappingAutoIntakeTests
{
    private const string Url = "http://localhost:8000";
    private const string Token = "dgk_test-session-token";

    private sealed class RecordingHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, string, HttpResponseMessage> _respond;

        public RecordingHandler(Func<HttpRequestMessage, string, HttpResponseMessage> respond) => _respond = respond;

        public List<(HttpMethod Method, string Uri, string? Auth, string Body)> Requests { get; } = new();

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var body = request.Content is null ? string.Empty : await request.Content.ReadAsStringAsync(cancellationToken);
            Requests.Add((request.Method, request.RequestUri!.AbsoluteUri, request.Headers.Authorization?.ToString(), body));
            return _respond(request, body);
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode code, string json) =>
        new(code) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    private static MappingSnapshot Snapshot(bool reversed = false)
    {
        var elements = new List<MappingElement>
        {
            new()
            {
                NativeId = "gh:doc:aa:{0;0}:0",
                Source = "Join Curves",
                Names = new[] { "OBJECT STATE: HexagonalUnit", "Ширина соты" },
                Geometry = new Dictionary<string, object> { ["vertexCount"] = 6, ["zMinM"] = 1.23456789 },
                Properties = new Dictionary<string, object> { ["hasVertexCount"] = 6 },
            },
            new()
            {
                NativeId = "gh:doc:bb:{0;1}:0",
                Source = "Panels",
                Geometry = new Dictionary<string, object> { ["vertexCount"] = 4 },
            },
        };
        if (reversed)
        {
            elements.Reverse();
        }

        return new MappingSnapshot
        {
            Elements = elements,
            Parameters = new[] { new MappingParameter { NativeId = "gh:doc:slider:1", Name = "Module Width F1", Names = new[] { "Ширина соты" }, Value = 6000, Min = 2800, Max = 12000 } },
        };
    }

    [Fact]
    public void Snapshot_RequestJson_CarriesNamesAndSliders()
    {
        using var doc = JsonDocument.Parse(Snapshot().ToRequestJson("v12", "label"));
        var root = doc.RootElement;
        Assert.Equal("grasshopper", root.GetProperty("platform").GetString());
        Assert.Equal("v12", root.GetProperty("project").GetString());
        var first = root.GetProperty("elements")[0];
        Assert.Equal("gh:doc:aa:{0;0}:0", first.GetProperty("nativeId").GetString());
        Assert.Equal("OBJECT STATE: HexagonalUnit", first.GetProperty("names")[0].GetString());
        Assert.Equal(1.234568, first.GetProperty("geometry").GetProperty("zMinM").GetDouble(), 6);
        var slider = root.GetProperty("parameters")[0];
        Assert.Equal("Module Width F1", slider.GetProperty("name").GetString());
        Assert.Equal(6000, slider.GetProperty("value").GetDouble());
    }

    [Fact]
    public void Snapshot_Fingerprint_IgnoresOrderAndLabel_ChangesWithContent()
    {
        var a = Snapshot();
        var b = Snapshot(reversed: true);
        Assert.Equal(a.Fingerprint(), b.Fingerprint());
        Assert.Equal(16, a.Fingerprint().Length);
        var changed = new MappingSnapshot
        {
            Elements = a.Elements,
            Parameters = new[] { new MappingParameter { NativeId = "gh:doc:slider:1", Name = "Module Width F1", Value = 4400 } },
        };
        Assert.NotEqual(a.Fingerprint(), changed.Fingerprint());
        Assert.False(a.IsEmpty);
        Assert.True(new MappingSnapshot().IsEmpty);
    }

    [Fact]
    public async Task Client_Create_SendsTokenOnlyInHeader_AndParsesSession()
    {
        const string session = """
        {"sessionId":"ms-0123456789ab","summary":{"total":2,"confirmed":0,"auto":0,"suggested":1,"ambiguous":1,"unmapped":0,"openQuestions":2,
         "parameters":{"total":1}},
         "elements":[{"nativeId":"gh:doc:aa:{0;0}:0","state":"ambiguous","roles":[]},
                     {"nativeId":"gh:doc:bb:{0;1}:0","state":"suggested","roles":[{"classIri":"ex:GlassPanel","label":"GlassPanel"}]}],
         "parameters":[{"nativeId":"gh:doc:slider:1","name":"Module Width F1","state":"ambiguous","property":null,
                        "candidates":[{"propertyIri":"ex:hasWidthM","label":"hasWidthM"}]}]}
        """;
        var handler = new RecordingHandler((_, _) => Json(HttpStatusCode.OK, session));
        var client = new MappingSessionClient(handler);

        var result = await client.CreateAsync(Url, Token, Snapshot().ToRequestJson("v12", "x"));

        Assert.True(result.Ok);
        var request = Assert.Single(handler.Requests);
        Assert.Equal(HttpMethod.Post, request.Method);
        Assert.Equal($"{Url}/mapping/sessions", request.Uri);
        Assert.Equal($"Bearer {Token}", request.Auth);
        Assert.DoesNotContain(Token, request.Uri);
        Assert.DoesNotContain(Token, request.Body);
        var state = result.Value!;
        Assert.Equal("ms-0123456789ab", state.SessionId);
        Assert.Equal(2, state.OpenQuestions);
        Assert.Equal("suggested", state.Elements["gh:doc:bb:{0;1}:0"].State);
        Assert.Equal(new[] { "GlassPanel" }, state.Elements["gh:doc:bb:{0;1}:0"].RoleLabels);
        var slider = Assert.Single(state.Parameters);
        Assert.Equal("hasWidthM", slider.PropertyLabel);
        Assert.Equal(16, state.Revision.Length);
    }

    [Fact]
    public async Task Client_Revision_ChangesWhenAnAnswerChangesAState()
    {
        var before = MappingSessionClient.ParseSession("""{"sessionId":"s","summary":{"openQuestions":1},"elements":[{"nativeId":"a","state":"ambiguous","roles":[]}]}""");
        var after = MappingSessionClient.ParseSession("""{"sessionId":"s","summary":{"openQuestions":0},"elements":[{"nativeId":"a","state":"confirmed","roles":[{"classIri":"ex:GroundFloorUnit","label":"GroundFloorUnit"}]}]}""");
        Assert.NotEqual(before.Revision, after.Revision);
        Assert.Equal(0, after.OpenQuestions);

        var handler = new RecordingHandler((_, _) => Json(HttpStatusCode.OK, """{"sessionId":"s","summary":{"openQuestions":0},"elements":[]}"""));
        var client = new MappingSessionClient(handler);
        var got = await client.GetAsync(Url, Token, "v12 project", "ms-0123456789ab");
        Assert.True(got.Ok);
        Assert.Equal($"{Url}/mapping/sessions/ms-0123456789ab?project=v12%20project", handler.Requests[0].Uri);
    }

    [Fact]
    public void Client_ParsesCanvasTags_FromProposalAndAnswerRows()
    {
        // Plan 1303-10: every proposed component gets a temporary frame and tag on the canvas.
        const string json = """
        {"sessionId":"s","document":"facade","summary":{"openQuestions":1},"elements":[],
         "questions":[{"questionId":"Q-1","type":"mapping-or-design","items":[
            {"itemId":"G-1","kind":"stream","name":"Panels A","componentId":"24549b0264794f1bb333b7768ab72820","count":120,
             "proposal":{"iri":"ex:GlassPanel","label":"GlassPanel"},"alternatives":[{"iri":"ex:BottomTriangularPanel","label":"BottomTriangularPanel"}],"state":"ambiguous"},
            {"itemId":"G-2","kind":"stream","name":"Revit","componentId":null,"count":3,"proposal":null,"alternatives":[],"state":"ambiguous"}]}],
         "answers":[{"answerId":"A-1","items":[
            {"itemId":"m1","kind":"measure","name":"AR (C#)","componentId":"71de70f3be6c494485dfa75af7e598e1","count":125,
             "proposal":{"iri":"ex:hasAspectRatio","label":"hasAspectRatio"},"alternatives":[],"state":"confirmed"}]}]}
        """;
        var state = MappingSessionClient.ParseSession(json);
        Assert.Equal("facade", state.Document);
        Assert.Equal(2, state.Tags.Count);
        var open = state.Tags[0];
        Assert.Equal("24549b0264794f1bb333b7768ab72820", open.ComponentId);
        Assert.Equal("ambiguous", open.State);
        Assert.Equal("DG ? Panels A → GlassPanel | BottomTriangularPanel", open.Text);
        Assert.Equal("DG ✓ AR (C#) → hasAspectRatio", state.Tags[1].Text);
        // An undo (the answer disappears) changes the revision, so CONNECTOR redraws.
        var undone = MappingSessionClient.ParseSession(json.Replace("\"answers\":[{", "\"answersX\":[{"));
        Assert.NotEqual(state.Revision, undone.Revision);
        Assert.Equal("DG · W → hasWidthM", MappingSessionClient.TagText("suggested", "W", "hasWidthM", new[] { "hasAspectRatio" }));
    }

    [Fact]
    public void BridgeCommands_All_IncludeTheMappingCommands_ReadCommandsUnchanged()
    {
        // Plan 1303-10: DeGram focuses components and starts mapping through the canvas bridge.
        Assert.Equal("focus_component", DG.Core.Bridge.CanvasBridgeCommands.FocusComponent);
        Assert.Equal("start_mapping", DG.Core.Bridge.CanvasBridgeCommands.StartMapping);
        Assert.Equal("get_mapping_status", DG.Core.Bridge.CanvasBridgeCommands.GetMappingStatus);
        foreach (var c in new[] { "focus_component", "start_mapping", "get_mapping_status" })
        {
            Assert.Contains(c, DG.Core.Bridge.CanvasBridgeCommands.All);
            Assert.DoesNotContain(c, DG.Core.Bridge.CanvasBridgeCommands.ReadCommands);
        }
    }

    [Fact]
    public async Task Client_Receipt_DoesNotCommitOrSendDraftAnswers()
    {
        const string batch = """
        {"batchId":"batch-four","delivery":{"state":"written"},"payload":{"applied":2,
         "elements":[{"nativeId":"a","roles":["ex:HexagonalUnit"]},{"nativeId":"b","roles":["ex:GlassPanel","ex:FacadeModule"]}],
         "parameters":[{"nativeId":"gh:doc:slider:1","name":"Module Width F1"}],
         "measures":[{"nativeId":"gh:doc:measure:m1","name":"W","propertyIri":"ex:hasWidthM","stream":"PB"}]}}
        """;
        var handler = new RecordingHandler((_, _) => Json(HttpStatusCode.OK, batch));
        var result = await new MappingSessionClient(handler).AcknowledgeAsync(Url, Token, "v12", "s",
            "batch-four", new MappingDeliveryReceipt("written", 2, 0));

        Assert.True(result.Ok);
        var request = Assert.Single(handler.Requests);
        Assert.Equal("{\"project\":\"v12\",\"batchId\":\"batch-four\",\"delivery\":{\"state\":\"written\",\"written\":2,\"skipped\":0}}", request.Body);
        Assert.Equal($"Bearer {Token}", request.Auth);
        Assert.DoesNotContain(Token, request.Body);
        Assert.Equal(new[] { "ex:GlassPanel", "ex:FacadeModule" }, result.Value!.Payload.RolesByElement["b"]);
        Assert.Equal("Module Width F1", Assert.Single(result.Value.Payload.Parameters).Name);
        Assert.Equal("hasWidthM", Assert.Single(result.Value.Payload.Measures).PropertyLabel);
    }

    [Theory]
    [InlineData("{\"applied\":\"1\",\"elements\":[]}")]
    [InlineData("{\"applied\":1,\"elements\":[{\"nativeId\":\"a\",\"roles\":[\"ex:A\",\"ex:A\"]}]}")]
    [InlineData("{\"applied\":1,\"elements\":[{\"nativeId\":\"a\",\"roles\":[\"ex:A\"]},{\"nativeId\":\"a\",\"roles\":[\"ex:B\"]}]}")]
    [InlineData("{\"applied\":0,\"elements\":[],\"measures\":[{\"nativeId\":\"m\"}]}")]
    [InlineData("{\"applied\":0,\"elements\":[],\"parameters\":[{\"nativeId\":\"p\"},{\"nativeId\":\"p\"}]}")]
    public void Client_RejectsMalformedImmutableBatch(string payload)
    {
        Assert.Throws<FormatException>(() => MappingSessionClient.ParseBatch(
            "{\"batchId\":\"bad\",\"delivery\":{\"state\":\"queued\"},\"payload\":" + payload + "}"));
    }

    [Fact]
    public void Client_ExplicitBatches_AreIndependentOfOpenQuestionCount()
    {
        var state = MappingSessionClient.ParseSession("""
        {"sessionId":"s","revision":"123456789012345678901234","summary":{"openQuestions":6},
         "batches":[{"batchId":"four","delivery":{"state":"queued"},"payload":{"applied":1,
          "elements":[{"nativeId":"selected","roles":["ex:GlassPanel"]}]}},
         {"batchId":"later","delivery":{"state":"failed"},"payload":{"applied":0,"elements":[]}}]}
        """);
        Assert.Equal(6, state.OpenQuestions);
        Assert.Equal("123456789012345678901234", state.Revision);
        Assert.Equal(2, state.Batches.Count);
        Assert.Equal("queued", state.Batches[0].DeliveryState);
        Assert.Equal("selected", Assert.Single(state.Batches[0].Payload.RolesByElement).Key);
        Assert.Equal("failed", state.Batches[1].DeliveryState);
        var legacy = MappingSessionClient.ParseSession("""{"sessionId":"old","appliedAt":"2026-10-18"}""");
        Assert.NotNull(legacy.AppliedAt);
        Assert.Empty(legacy.Batches);
        Assert.Throws<FormatException>(() => MappingSessionClient.ParseBatch("""
        {"batchId":"bad","delivery":{"state":"queued"},"payload":{"applied":4,"elements":[]}}
        """));
    }

    [Fact]
    public async Task Client_Errors_ReturnCodes_WithoutThrowing()
    {
        var refused = new RecordingHandler((_, _) => Json(HttpStatusCode.Forbidden, """{"detail":{"code":"PROJECT_FORBIDDEN","message":"x"}}"""));
        var r1 = await new MappingSessionClient(refused).CreateAsync(Url, Token, "{}");
        Assert.False(r1.Ok);
        Assert.Equal(403, r1.Status);
        Assert.Equal("PROJECT_FORBIDDEN", r1.ErrorCode);

        var noToken = await new MappingSessionClient(refused).CreateAsync(Url, null, "{}");
        Assert.Equal("SIGN_IN_REQUIRED", noToken.ErrorCode);
        Assert.Empty(refused.Requests.Skip(1));

        var broken = new RecordingHandler((_, _) => throw new HttpRequestException("connection refused " + Token));
        var r2 = await new MappingSessionClient(broken).CreateAsync(Url, Token, "{}");
        Assert.Equal("UNREACHABLE", r2.ErrorCode);
    }

    [Fact]
    public void CanvasText_NestedGroupsAndScribbles()
    {
        var obj = Guid.NewGuid();
        var inner = new CanvasGroupInfo(Guid.NewGuid(), "Group B Panels", new[] { obj });
        var outer = new CanvasGroupInfo(Guid.NewGuid(), "ALL PANELS", new[] { inner.Id });
        var empty = new CanvasGroupInfo(Guid.NewGuid(), "  ", new[] { obj });
        var names = MappingCanvasText.GroupNamesByObject(new[] { inner, outer, empty });
        Assert.Equal(new[] { "Group B Panels", "ALL PANELS" }, names[obj]);
        Assert.False(names.ContainsKey(inner.Id));

        var near = new CanvasScribbleInfo(Guid.NewGuid(), "стеклянные\nпанели", 120, 40);
        var far = new CanvasScribbleInfo(Guid.NewGuid(), "far away", 5000, 5000);
        var bounds = new CanvasBounds(0, 0, 100, 50);
        Assert.Equal(new[] { "стеклянные панели" }, MappingCanvasText.ScribblesFor(obj, bounds, new[] { near, far }, new[] { inner }));
        var grouped = new CanvasGroupInfo(Guid.NewGuid(), "G", new[] { obj, far.Id });
        Assert.Contains("far away", MappingCanvasText.ScribblesFor(obj, bounds, new[] { far }, new[] { grouped }));
    }

    [Fact]
    public void CanvasText_DefaultNicknamesAndMerge()
    {
        Assert.True(MappingCanvasText.IsDefaultNickname("", "Number Slider"));
        Assert.True(MappingCanvasText.IsDefaultNickname("Number Slider", "Number Slider"));
        Assert.True(MappingCanvasText.IsDefaultNickname("number slider", "Slider", "Number Slider"));
        Assert.False(MappingCanvasText.IsDefaultNickname("Module Width F1", "Number Slider"));
        Assert.Equal(new[] { "a", "b" }, MappingCanvasText.Merge(new[] { "a", " ", null }, new[] { "b", "a" }));
        Assert.Equal(120, MappingCanvasText.Clean(new string('x', 300)).Length);
    }
}
