using DG.Core.Bridge;

namespace DG.Tests;

/// <summary>
/// Phase 1303-24 (D-67): the bounded wait for a UI hand-off reports an expiry to the caller so a hand-off that was
/// answered BUSY can be cancelled and never runs later.
/// </summary>
public class CanvasUiWaitTests
{
    [Fact]
    public void RunTimeout_IsLongerThanTheDefaultUiTimeout()
    {
        Assert.True(CanvasBridgeProtocol.CanvasRunUiTimeoutMs > CanvasBridgeProtocol.CanvasUiTimeoutMs);
        Assert.Equal(60000, CanvasBridgeProtocol.CanvasRunUiTimeoutMs);
    }

    [Fact]
    public void Await_Expiry_CallsOnTimeoutOnceAndThrowsBusy()
    {
        var tcs = new TaskCompletionSource<object?>();
        var calls = 0;

        var ex = Assert.Throws<CanvasBusyException>(() => CanvasUiWait.Await(tcs.Task, 50, () => calls++));

        Assert.Equal(1, calls);
        Assert.Contains("50 ms", ex.Message);
    }

    [Fact]
    public void Await_Completed_NeverCallsOnTimeout()
    {
        var tcs = new TaskCompletionSource<object?>();
        tcs.SetResult(42);
        var calls = 0;

        var result = CanvasUiWait.Await(tcs.Task, 50, () => calls++);

        Assert.Equal(42, result);
        Assert.Equal(0, calls);
    }

    [Fact]
    public void Await_Faulted_RethrowsTheOriginalExceptionWithoutOnTimeout()
    {
        var tcs = new TaskCompletionSource<object?>();
        tcs.SetException(new InvalidOperationException("boom"));
        var calls = 0;

        var ex = Assert.Throws<InvalidOperationException>(() => CanvasUiWait.Await(tcs.Task, 50, () => calls++));

        Assert.Equal("boom", ex.Message);
        Assert.Equal(0, calls);
    }

    [Fact]
    public void Await_TwoArgumentForm_StillWorks()
    {
        var tcs = new TaskCompletionSource<object?>();
        tcs.SetResult("ok");

        Assert.Equal("ok", CanvasUiWait.Await(tcs.Task, 50));
    }
}
