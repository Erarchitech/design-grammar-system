namespace DG.Core.Bridge;

/// <summary>
/// Phase 1303-24 (D-67): SendValid is a one-shot switch of the property check. Every Rhino.Inside re-solve with
/// SendValid True publishes the runs again (live 2026-10-25: a value left True published 50 runs in 54 minutes and
/// kept the canvas frozen), so when a solution ends with SendValid on the listener switches it off. Pure decision
/// logic: the Grasshopper side only reads the toggle, asks <see cref="Observe"/> and acts on the answer.
/// </summary>
public sealed class SendValidGuard
{
    private readonly int _loopThreshold;
    private readonly TimeSpan _window;
    private readonly List<DateTime> _recent = new();

    /// <param name="loopThreshold">Solution ends with SendValid on, within <paramref name="window"/>, that suggest a loop.</param>
    /// <param name="window">The sliding window; five minutes when null.</param>
    public SendValidGuard(int loopThreshold = 3, TimeSpan? window = null)
    {
        _loopThreshold = loopThreshold;
        _window = window ?? TimeSpan.FromMinutes(5);
    }

    /// <summary>Times SendValid was found on at a solution end and switched off.</summary>
    public int Disarmed { get; private set; }

    /// <summary>True once <c>loopThreshold</c> or more observations with SendValid on fell inside the window.</summary>
    public bool LoopSuspected { get; private set; }

    /// <summary>
    /// Called at the end of a solution with the current SendValid value. Returns true when SendValid must be
    /// switched off now (it is on); never when it is already off.
    /// </summary>
    public bool Observe(bool sendValidOn, DateTime utcNow)
    {
        if (!sendValidOn)
        {
            return false;
        }

        Disarmed++;
        _recent.RemoveAll(t => utcNow - t > _window);
        _recent.Add(utcNow);
        if (_recent.Count >= _loopThreshold)
        {
            LoopSuspected = true;
        }

        return true;
    }

    /// <summary>Clears the loop flag and the window; the total <see cref="Disarmed"/> is kept.</summary>
    public void Reset()
    {
        _recent.Clear();
        LoopSuspected = false;
    }
}
