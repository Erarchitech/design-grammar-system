namespace DG.Core.Bridge;

/// <summary>
/// Phase 1303-25 (D-70): decides when the property check's one-shot (SendValid and Paint) may be released. It is
/// released at the end of the solution that produced the check's verdict; a solution without one (METAGRAPH loads its
/// rules asynchronously and delivers them one solution later, live 2026-10-25) keeps it armed, but never for longer
/// than <c>maxSolutions</c> solution ends or <c>maxWait</c>, so a VALIDATOR that never gets a rule cannot keep
/// SendValid on. Pure decision logic: the Grasshopper side reports each solution end and acts on the answer.
/// </summary>
public sealed class VerdictGate
{
    private readonly int _maxSolutions;
    private readonly TimeSpan _maxWait;
    private int _waited;
    private DateTime _since;

    /// <param name="maxSolutions">Solution ends without a verdict after which the one-shot is released anyway.</param>
    /// <param name="maxWait">Time since the first solution end without a verdict after which it is released; 120 s when null.</param>
    public VerdictGate(int maxSolutions = 3, TimeSpan? maxWait = null)
    {
        _maxSolutions = maxSolutions;
        _maxWait = maxWait ?? TimeSpan.FromSeconds(120);
    }

    /// <summary>True while solutions without a verdict are being waited through.</summary>
    public bool Pending => _waited > 0;

    /// <summary>
    /// Called at the end of a solution of an armed check. Returns true when the one-shot must be released now.
    /// </summary>
    public bool Observe(bool verdictProduced, DateTime utcNow)
    {
        if (verdictProduced)
        {
            Clear();
            return true;
        }

        if (_waited == 0)
        {
            _since = utcNow;
        }

        _waited++;
        if (_waited >= _maxSolutions || utcNow - _since >= _maxWait)
        {
            Clear();
            return true;
        }

        return false;
    }

    /// <summary>Forgets a pending wait (a new run is armed, or SendValid went off by other means).</summary>
    public void Clear() => _waited = 0;
}
