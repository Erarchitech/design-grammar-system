using System.Text.Json;
using DG.Core.Bridge;

namespace DG.Tests;

public class CanvasBridgeDispatcherTests
{
    // --- Task 1: CanvasBridgeProtocol / CanvasCommandRequest / CanvasListenerRequestKey ---

    [Fact]
    public void TryParse_WellFormedLine_ReturnsTrueWithParsedType()
    {
        var ok = CanvasBridgeProtocol.TryParse(
            "{\"type\":\"get_selection\",\"parameters\":{}}",
            out var request);

        Assert.True(ok);
        Assert.Equal(CanvasBridgeCommands.GetSelection, request.Type);
    }

    [Fact]
    public void TryParse_BomPrefixedLine_StripsBomAndReturnsTrue()
    {
        var line = "﻿{\"type\":\"get_selection\",\"parameters\":{}}";

        var ok = CanvasBridgeProtocol.TryParse(line, out var request);

        Assert.True(ok);
        Assert.Equal(CanvasBridgeCommands.GetSelection, request.Type);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("{not json")]
    public void TryParse_NullOrWhitespaceOrMalformed_ReturnsFalseWithoutThrowing(string? line)
    {
        var ok = CanvasBridgeProtocol.TryParse(line, out _);

        Assert.False(ok);
    }

    [Fact]
    public void TryParse_OversizedLine_ReturnsFalseWithoutThrowingOrOom()
    {
        // 5 MB + a bit, well past CanvasBridgeProtocol.MaxRequestBytes.
        var oversized = "{\"type\":\"get_selection\",\"parameters\":{\"pad\":\""
            + new string('x', CanvasBridgeProtocol.MaxRequestBytes + 1024)
            + "\"}}";

        var ok = CanvasBridgeProtocol.TryParse(oversized, out _);

        Assert.False(ok);
    }

    [Fact]
    public void BuildOk_SerializesHandshakeFieldsAndResultAsSingleLine()
    {
        var line = CanvasBridgeProtocol.BuildOk(new { selection = new[] { "g1" } });

        Assert.DoesNotContain("\n", line);

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;

        Assert.Equal("dg", root.GetProperty("bridge").GetString());
        Assert.Equal(1, root.GetProperty("version").GetInt32());
        Assert.Equal("ok", root.GetProperty("status").GetString());
        Assert.Equal("g1", root.GetProperty("result").GetProperty("selection")[0].GetString());
    }

    [Fact]
    public void BuildError_SerializesHandshakeFieldsAndErrorDetail()
    {
        var line = CanvasBridgeProtocol.BuildError("boom", "BAD_REQUEST");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;

        Assert.Equal("dg", root.GetProperty("bridge").GetString());
        Assert.Equal(1, root.GetProperty("version").GetInt32());
        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("BAD_REQUEST", root.GetProperty("error").GetProperty("code").GetString());
        Assert.Equal("boom", root.GetProperty("error").GetProperty("message").GetString());
    }

    [Fact]
    public void CanvasListenerRequestKey_Build_DerivesOnlyFromRunAndPort()
    {
        Assert.Equal("true|8720", CanvasListenerRequestKey.Build(true, 8720));
        Assert.NotEqual(
            CanvasListenerRequestKey.Build(true, 8720),
            CanvasListenerRequestKey.Build(false, 8720));
        Assert.NotEqual(
            CanvasListenerRequestKey.Build(true, 8720),
            CanvasListenerRequestKey.Build(true, 8721));
    }

    // --- Task 2: CanvasCommandDispatcher ---

    [Fact]
    public void Dispatch_WellFormedAllowListedCommand_RoutesToHandlerAndReturnsOk()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetSelection] = _ => new { selection = new[] { "a" } },
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_selection\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("ok", root.GetProperty("status").GetString());
        Assert.Equal("a", root.GetProperty("result").GetProperty("selection")[0].GetString());
    }

    [Fact]
    public void Dispatch_PreviewCommand_ReturnsStubNotSupportedPayload()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.PreviewStructure] =
                _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.PreviewStructure),
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"preview_structure\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("ok", root.GetProperty("status").GetString());
        Assert.False(root.GetProperty("result").GetProperty("supported").GetBoolean());
        Assert.Equal("preview_structure", root.GetProperty("result").GetProperty("command").GetString());
        Assert.Contains("Not supported", root.GetProperty("result").GetProperty("message").GetString());
    }

    [Fact]
    public void Dispatch_UnknownWriteCommand_ReturnsUnknownCommandError()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetSelection] = _ => new { selection = Array.Empty<string>() },
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"add_component\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("UNKNOWN_COMMAND", root.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public void Dispatch_MalformedLine_ReturnsBadRequestError()
    {
        var dispatcher = new CanvasCommandDispatcher(
            new Dictionary<string, Func<CanvasCommandRequest, object?>>());

        var line = dispatcher.Dispatch("{ not json");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("BAD_REQUEST", root.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public void Dispatch_HandlerThrows_ReturnsHandlerErrorWithoutPropagating()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetSelection] = _ => throw new InvalidOperationException("kaboom"),
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_selection\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("HANDLER_ERROR", root.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public void Dispatch_HandlerMapOmitsCommand_MakesItUnreachable()
    {
        // A handler map that only wires get_selection means get_canvas_context is unreachable.
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetSelection] = _ => new { selection = Array.Empty<string>() },
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_canvas_context\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("UNKNOWN_COMMAND", root.GetProperty("error").GetProperty("code").GetString());
    }
}
