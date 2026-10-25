using DG.Core.Bridge;

namespace DG.Tests;

/// <summary>
/// Phase 1303-25 (D-70): the SendValid/Paint one-shot is released at the end of the solution that produced the
/// check's verdict. Live 2026-10-25: METAGRAPH delivered its rules one solution after a fresh placement; the one-shot
/// had already switched SendValid off, VALIDATOR answered "Rule input is required" and nothing was published.
/// </summary>
public class VerdictGateTests
{
    private static readonly DateTime T0 = new(2026, 10, 25, 15, 34, 0, DateTimeKind.Utc);

    [Fact]
    public void VerdictProduced_ReleasesAtOnce()
    {
        var gate = new VerdictGate();

        Assert.True(gate.Observe(true, T0));
        Assert.False(gate.Pending);
    }

    [Fact]
    public void NoVerdict_WaitsForTheNextSolution()
    {
        var gate = new VerdictGate();

        Assert.False(gate.Observe(false, T0));
        Assert.True(gate.Pending);
        Assert.True(gate.Observe(true, T0.AddSeconds(3)));
        Assert.False(gate.Pending);
    }

    [Fact]
    public void ThirdSolutionWithoutVerdict_Releases()
    {
        var gate = new VerdictGate();

        Assert.False(gate.Observe(false, T0));
        Assert.False(gate.Observe(false, T0.AddSeconds(1)));
        Assert.True(gate.Observe(false, T0.AddSeconds(2)));
        Assert.False(gate.Pending);
    }

    [Fact]
    public void WaitLongerThanTheBound_Releases()
    {
        var gate = new VerdictGate();

        Assert.False(gate.Observe(false, T0));
        Assert.True(gate.Observe(false, T0.AddSeconds(121)));
    }

    [Fact]
    public void AfterARelease_TheCountStartsAgain()
    {
        var gate = new VerdictGate();
        gate.Observe(false, T0);
        gate.Observe(false, T0.AddSeconds(1));
        gate.Observe(false, T0.AddSeconds(2)); // released by the bound

        Assert.False(gate.Observe(false, T0.AddSeconds(3)));
        Assert.True(gate.Pending);
    }

    [Fact]
    public void Clear_ForgetsAPendingWait()
    {
        var gate = new VerdictGate();
        gate.Observe(false, T0);
        gate.Observe(false, T0.AddSeconds(1));

        gate.Clear();

        Assert.False(gate.Pending);
        Assert.False(gate.Observe(false, T0.AddSeconds(2)));
        Assert.False(gate.Observe(false, T0.AddSeconds(3)));
    }

    [Fact]
    public void Bounds_AreConfigurable()
    {
        var gate = new VerdictGate(maxSolutions: 1, maxWait: TimeSpan.FromSeconds(5));

        Assert.True(gate.Observe(false, T0));
    }
}
