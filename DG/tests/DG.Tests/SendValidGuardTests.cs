using DG.Core.Bridge;

namespace DG.Tests;

/// <summary>
/// Phase 1303-24 (D-67): SendValid is one-shot on the canvas. Live 2026-10-25: a SendValid left True made every
/// re-solve publish (50 runs in 54 minutes).
/// </summary>
public class SendValidGuardTests
{
    private static readonly DateTime T0 = new(2026, 10, 25, 9, 0, 0, DateTimeKind.Utc);

    [Fact]
    public void SendValidOff_NeverDisarms()
    {
        var guard = new SendValidGuard();

        Assert.False(guard.Observe(false, T0));
        Assert.Equal(0, guard.Disarmed);
        Assert.False(guard.LoopSuspected);
    }

    [Fact]
    public void SendValidOn_DisarmsAndCounts()
    {
        var guard = new SendValidGuard();

        Assert.True(guard.Observe(true, T0));
        Assert.Equal(1, guard.Disarmed);
        Assert.False(guard.LoopSuspected);
    }

    [Fact]
    public void ThreeOnObservationsWithinFiveMinutes_SuspectALoop()
    {
        var guard = new SendValidGuard();

        guard.Observe(true, T0);
        guard.Observe(true, T0.AddMinutes(1));
        Assert.False(guard.LoopSuspected);
        guard.Observe(true, T0.AddMinutes(2));

        Assert.True(guard.LoopSuspected);
        Assert.Equal(3, guard.Disarmed);
    }

    [Fact]
    public void ObservationsOutsideTheWindow_DoNotSuspectALoop()
    {
        var guard = new SendValidGuard();

        guard.Observe(true, T0);
        guard.Observe(true, T0.AddMinutes(2));
        guard.Observe(true, T0.AddMinutes(6)); // the first one is older than 5 minutes now

        Assert.False(guard.LoopSuspected);
        Assert.Equal(3, guard.Disarmed);
    }

    [Fact]
    public void OffObservations_DoNotCountTowardsALoop()
    {
        var guard = new SendValidGuard();

        guard.Observe(true, T0);
        guard.Observe(false, T0.AddSeconds(10));
        guard.Observe(true, T0.AddSeconds(20));
        guard.Observe(false, T0.AddSeconds(30));

        Assert.False(guard.LoopSuspected);
        Assert.Equal(2, guard.Disarmed);
    }

    [Fact]
    public void Reset_ClearsTheLoopFlagButKeepsTheTotal()
    {
        var guard = new SendValidGuard();
        guard.Observe(true, T0);
        guard.Observe(true, T0.AddSeconds(1));
        guard.Observe(true, T0.AddSeconds(2));
        Assert.True(guard.LoopSuspected);

        guard.Reset();

        Assert.False(guard.LoopSuspected);
        Assert.Equal(3, guard.Disarmed);
    }
}
