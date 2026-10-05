using System.Text.Json;
using DG.Core.Bridge;

namespace DG.Tests;

/// <summary>
/// Phase 1301 plan 06 (D-13/D-14/D-18, DGCL-04/DGCL-06): the read-only
/// get_document_identity bridge command and the BUSY outcome of a bounded
/// UI-thread wait. Everything here is GH-SDK independent (DG.Core only).
/// </summary>
public class CanvasDocumentIdentityTests
{
    private static readonly DateTimeOffset Captured = new(2026, 10, 5, 12, 0, 0, TimeSpan.Zero);

    // --- Task 1: identity payload + read command ---

    [Fact]
    public void Identity_Serializes_CamelCase_With_All_Fields()
    {
        var identity = new CanvasDocumentIdentity(
            "7f3c0a52-1111-2222-3333-444455556666",
            @"C:\work\tower.gh",
            "tower",
            true,
            Captured);

        var line = CanvasBridgeProtocol.BuildOk(identity);

        using var doc = JsonDocument.Parse(line);
        var result = doc.RootElement.GetProperty("result");

        Assert.Equal("7f3c0a52-1111-2222-3333-444455556666", result.GetProperty("documentId").GetString());
        Assert.Equal(@"C:\work\tower.gh", result.GetProperty("filePath").GetString());
        Assert.Equal("tower", result.GetProperty("displayName").GetString());
        Assert.True(result.GetProperty("isModified").GetBoolean());
        Assert.Equal(Captured, result.GetProperty("capturedAt").GetDateTimeOffset());
    }

    [Fact]
    public void Identity_UnsavedDocument_FilePath_Is_Json_Null()
    {
        var identity = new CanvasDocumentIdentity("doc-1", null, "Untitled", false, Captured);

        var line = CanvasBridgeProtocol.BuildOk(identity);

        using var doc = JsonDocument.Parse(line);
        var result = doc.RootElement.GetProperty("result");

        Assert.Equal(JsonValueKind.Null, result.GetProperty("filePath").ValueKind);
        Assert.False(result.GetProperty("isModified").GetBoolean());
    }

    [Fact]
    public void Dispatcher_StubIdentityHandler_Returns_Ok_With_Identity_Payload()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetDocumentIdentity] = _ =>
                new CanvasDocumentIdentity("doc-9", null, "Untitled", false, Captured),
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_document_identity\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;

        Assert.Equal("ok", root.GetProperty("status").GetString());
        Assert.Equal("doc-9", root.GetProperty("result").GetProperty("documentId").GetString());
    }

    [Fact]
    public void Command_Constant_And_Read_Set_Contain_Identity()
    {
        Assert.Equal("get_document_identity", CanvasBridgeCommands.GetDocumentIdentity);
        Assert.Contains(CanvasBridgeCommands.GetDocumentIdentity, CanvasBridgeCommands.All);
        Assert.Contains(CanvasBridgeCommands.GetDocumentIdentity, CanvasBridgeCommands.ReadCommands);
    }

    [Fact]
    public void ReadCommands_Are_Exactly_The_Four_Read_Only_Commands()
    {
        Assert.Equal(
            new[] { "get_canvas_context", "get_selection", "get_preview_status", "get_document_identity" }
                .OrderBy(x => x, StringComparer.Ordinal),
            CanvasBridgeCommands.ReadCommands.OrderBy(x => x, StringComparer.Ordinal));
    }

    [Fact]
    public void ReadCommands_Exclude_Mutating_Preview_Commands()
    {
        Assert.DoesNotContain(CanvasBridgeCommands.PreviewStructure, CanvasBridgeCommands.ReadCommands);
        Assert.DoesNotContain(CanvasBridgeCommands.ClearPreview, CanvasBridgeCommands.ReadCommands);
    }

    [Fact]
    public void Dispatcher_UnregisteredCommand_Still_UNKNOWN_COMMAND()
    {
        var dispatcher = new CanvasCommandDispatcher(
            new Dictionary<string, Func<CanvasCommandRequest, object?>>());

        var line = dispatcher.Dispatch("{\"type\":\"get_document_identity\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        Assert.Equal("UNKNOWN_COMMAND", doc.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    // --- Task 2: bounded UI-thread wait -> BUSY ---

    [Fact]
    public void Protocol_Exposes_Busy_Code_And_Ten_Second_Ui_Timeout()
    {
        Assert.Equal("BUSY", CanvasBridgeProtocol.ErrorCodeBusy);
        Assert.Equal(10000, CanvasBridgeProtocol.CanvasUiTimeoutMs);
    }

    [Fact]
    public void BuildError_Busy_Yields_Error_Envelope_With_Busy_Code()
    {
        var line = CanvasBridgeProtocol.BuildError("Canvas UI thread is busy.", CanvasBridgeProtocol.ErrorCodeBusy);

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;

        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("BUSY", root.GetProperty("error").GetProperty("code").GetString());
        Assert.Equal("Canvas UI thread is busy.", root.GetProperty("error").GetProperty("message").GetString());
    }

    [Fact]
    public void Await_NeverCompletingTask_Throws_CanvasBusyException_After_Timeout()
    {
        var never = new TaskCompletionSource<object?>();

        var ex = Assert.Throws<CanvasBusyException>(() => CanvasUiWait.Await(never.Task, 50));

        Assert.Contains("busy", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Await_CompletedTask_Returns_Result()
    {
        var done = new TaskCompletionSource<object?>();
        done.SetResult("hello");

        Assert.Equal("hello", CanvasUiWait.Await(done.Task, 1000));
    }

    [Fact]
    public void Await_FaultedTask_Rethrows_Original_Exception_Not_Busy()
    {
        var faulted = new TaskCompletionSource<object?>();
        faulted.SetException(new InvalidOperationException("boom"));

        var ex = Assert.Throws<InvalidOperationException>(() => CanvasUiWait.Await(faulted.Task, 1000));

        Assert.Equal("boom", ex.Message);
    }

    [Fact]
    public void Dispatcher_Handler_Waiting_On_Stuck_Ui_Task_Returns_Busy_Envelope()
    {
        var never = new TaskCompletionSource<object?>();
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetDocumentIdentity] = _ => CanvasUiWait.Await(never.Task, 50),
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_document_identity\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;

        Assert.Equal("error", root.GetProperty("status").GetString());
        Assert.Equal("BUSY", root.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public void Dispatcher_Handler_Exception_Is_Still_HANDLER_ERROR()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetSelection] = _ => throw new InvalidOperationException("nope"),
        };
        var dispatcher = new CanvasCommandDispatcher(handlers);

        var line = dispatcher.Dispatch("{\"type\":\"get_selection\",\"parameters\":{}}");

        using var doc = JsonDocument.Parse(line);
        Assert.Equal("HANDLER_ERROR", doc.RootElement.GetProperty("error").GetProperty("code").GetString());
    }
}
