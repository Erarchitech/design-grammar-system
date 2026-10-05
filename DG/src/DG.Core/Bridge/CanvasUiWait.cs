namespace DG.Core.Bridge;

/// <summary>
/// Thrown when a UI-thread-marshalled canvas operation does not complete within
/// <see cref="CanvasBridgeProtocol.CanvasUiTimeoutMs"/>. The dispatcher maps it
/// to the <see cref="CanvasBridgeProtocol.ErrorCodeBusy"/> error envelope.
/// </summary>
public sealed class CanvasBusyException : Exception
{
    public CanvasBusyException(string message)
        : base(message)
    {
    }
}

/// <summary>
/// GH-SDK independent bounded wait for a UI-marshalled task (Phase 1301
/// D-18/DGCL-06). The listener accept loop serves one client at a time, so an
/// unbounded wait on a stuck Rhino UI thread would hang every later request;
/// a bounded wait turns that into a diagnosable BUSY outcome.
/// </summary>
public static class CanvasUiWait
{
    /// <summary>
    /// Waits for <paramref name="task"/> up to <paramref name="timeoutMs"/>.
    /// Returns its result; rethrows its original exception when it faults;
    /// throws <see cref="CanvasBusyException"/> on expiry. A timed-out task is
    /// not cancelled (the UI delegate may still run later) and is never retried.
    /// </summary>
    public static T Await<T>(Task<T> task, int timeoutMs = CanvasBridgeProtocol.CanvasUiTimeoutMs)
    {
        ArgumentNullException.ThrowIfNull(task);

        // WaitHandle wait never throws for a faulted task (Task.Wait would wrap in AggregateException).
        if (!((IAsyncResult)task).AsyncWaitHandle.WaitOne(timeoutMs) && !task.IsCompleted)
        {
            throw new CanvasBusyException(
                $"Canvas UI thread did not respond within {timeoutMs} ms (busy). Retry later.");
        }

        // Completed: unwrap so the original exception (not AggregateException) surfaces.
        return task.GetAwaiter().GetResult();
    }
}
