namespace DG.Core.Bridge;

/// <summary>
/// Builds the deduplication key CanvasListenerComponent (Plan 02) uses to decide
/// whether SolveInstance needs to (re)start the TCP listener. The key is a
/// deterministic function of (Run, Port) only — nothing else in the document
/// should ever change it (see 33-RESEARCH.md Pitfall 3).
/// </summary>
public static class CanvasListenerRequestKey
{
    public static string Build(bool run, int port)
    {
        return $"{run.ToString().ToLowerInvariant()}|{port}";
    }
}
