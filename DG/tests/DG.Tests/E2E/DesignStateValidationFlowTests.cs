using System.Net.Http.Json;
using System.Text.Json;
using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Services;
using Neo4j.Driver;

namespace DG.Tests.E2E;

[Trait("Category", "E2E")]
public sealed class DesignStateValidationFlowTests : IAsyncLifetime
{
    private const string Neo4jUri = "bolt://localhost:7687";
    private const string Neo4jUser = "neo4j";
    private const string Neo4jPassword = "12345678";
    private const string DataServiceBase = "http://localhost:8000";
    private const string TestProject = "e2e-test-phase6";

    private IDriver _driver = null!;
    private HttpClient _http = null!;

    public async Task InitializeAsync()
    {
        _driver = GraphDatabase.Driver(Neo4jUri, AuthTokens.Basic(Neo4jUser, Neo4jPassword));
        _http = new HttpClient { BaseAddress = new Uri(DataServiceBase) };

        // Assert stack is up
        await using var session = _driver.AsyncSession();
        await session.RunAsync("RETURN 1");

        // Clean up any leftover test data
        await CleanupTestProject();
    }

    public async Task DisposeAsync()
    {
        await CleanupTestProject();
        _http.Dispose();
        await _driver.DisposeAsync();
    }

    private async Task CleanupTestProject()
    {
        await using var session = _driver.AsyncSession();
        await session.RunAsync(
            "MATCH (n {project: $project}) DETACH DELETE n",
            new { project = TestProject });
    }

    // ── Scenario 1: Happy path — state publish and retrieve (INTG-01) ──────────

    [Fact]
    public async Task HappyPath_StatePublishAndRetrieve()
    {
        // Build a snapshot with 2 parameters
        var snapshot = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "height", DisplayName = "Height",
                Type = DesignStateParameterType.Number, NumberValue = 75.0,
            },
            new DesignStateParameter
            {
                ParameterId = "isActive", DisplayName = "Is Active",
                Type = DesignStateParameterType.Boolean, BooleanValue = true,
            });

        var statePayloadJson = DesignStateJsonSerializer.Serialize(snapshot);
        var runId = $"e2e-run-{Guid.NewGuid():N}";

        // Seed a ValidationRun node directly in Neo4j with state
        await using var session = _driver.AsyncSession();
        await session.RunAsync(
            """
            CREATE (r:ValidationRun {
                runId: $runId,
                project: $project,
                graph: 'ValidGraph',
                createdAt: datetime(),
                rulesJson: '[]',
                statePayloadJson: $statePayloadJson
            })
            """,
            new { runId, project = TestProject, statePayloadJson });

        // Call GET /validation/runs/{TestProject}
        var response = await _http.GetAsync($"/validation/runs/{TestProject}");
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        var runs = doc.RootElement.GetProperty("runs");
        Assert.True(runs.GetArrayLength() >= 1);

        // Find our run
        JsonElement? foundRun = null;
        foreach (var run in runs.EnumerateArray())
        {
            if (run.GetProperty("runId").GetString() == runId)
            {
                foundRun = run;
                break;
            }
        }

        Assert.NotNull(foundRun);
        var state = foundRun.Value.GetProperty("state");
        Assert.NotEqual(JsonValueKind.Null, state.ValueKind);
        Assert.Equal(snapshot.StateId, state.GetProperty("stateId").GetString());
        Assert.Equal(2, state.GetProperty("parameterCount").GetInt32());
    }

    // ── Scenario 2: Legacy no-state flow (INTG-02) ─────────────────────────────

    [Fact]
    public async Task LegacyNoState_FlowStillWorks()
    {
        var runId = $"e2e-nostate-{Guid.NewGuid():N}";

        // Seed a ValidationRun WITHOUT statePayloadJson
        await using var session = _driver.AsyncSession();
        await session.RunAsync(
            """
            CREATE (r:ValidationRun {
                runId: $runId,
                project: $project,
                graph: 'ValidGraph',
                createdAt: datetime(),
                rulesJson: '[]'
            })
            """,
            new { runId, project = TestProject });

        // Call GET /validation/runs/{TestProject}
        var response = await _http.GetAsync($"/validation/runs/{TestProject}");
        Assert.Equal(System.Net.HttpStatusCode.OK, response.StatusCode);

        var json = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        var runs = doc.RootElement.GetProperty("runs");

        // Find our no-state run
        JsonElement? foundRun = null;
        foreach (var run in runs.EnumerateArray())
        {
            if (run.GetProperty("runId").GetString() == runId)
            {
                foundRun = run;
                break;
            }
        }

        Assert.NotNull(foundRun);
        // State should be null for runs without statePayloadJson
        var state = foundRun.Value.GetProperty("state");
        Assert.Equal(JsonValueKind.Null, state.ValueKind);
    }

    // ── Scenario 3: Filtering — state and rule data integrity ──────────────────

    [Fact]
    public async Task Filtering_StateAndRule()
    {
        var snapshotA = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "height", DisplayName = "Height",
                Type = DesignStateParameterType.Number, NumberValue = 75.0,
            });
        var snapshotB = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "setback", DisplayName = "Setback",
                Type = DesignStateParameterType.Number, NumberValue = 5.0,
            });

        var runIdA = $"e2e-filter-A-{Guid.NewGuid():N}";
        var runIdB = $"e2e-filter-B-{Guid.NewGuid():N}";
        var runIdC = $"e2e-filter-C-{Guid.NewGuid():N}";

        await using var session = _driver.AsyncSession();

        // Run A: has rules and state A
        await session.RunAsync(
            """
            CREATE (r:ValidationRun {
                runId: $runId, project: $project, graph: 'ValidGraph',
                createdAt: datetime(),
                rulesJson: $rulesJson,
                statePayloadJson: $statePayloadJson
            })
            """,
            new
            {
                runId = runIdA, project = TestProject,
                rulesJson = "[{\"ruleId\":\"R_HEIGHT\"}]",
                statePayloadJson = DesignStateJsonSerializer.Serialize(snapshotA),
            });

        // Run B: has rules and state B
        await session.RunAsync(
            """
            CREATE (r:ValidationRun {
                runId: $runId, project: $project, graph: 'ValidGraph',
                createdAt: datetime(),
                rulesJson: $rulesJson,
                statePayloadJson: $statePayloadJson
            })
            """,
            new
            {
                runId = runIdB, project = TestProject,
                rulesJson = "[{\"ruleId\":\"R_SETBACK\"}]",
                statePayloadJson = DesignStateJsonSerializer.Serialize(snapshotB),
            });

        // Run C: has rules but NO state
        await session.RunAsync(
            """
            CREATE (r:ValidationRun {
                runId: $runId, project: $project, graph: 'ValidGraph',
                createdAt: datetime(),
                rulesJson: $rulesJson
            })
            """,
            new
            {
                runId = runIdC, project = TestProject,
                rulesJson = "[{\"ruleId\":\"R_HEIGHT\"}]",
            });

        // Retrieve all runs
        var response = await _http.GetAsync($"/validation/runs/{TestProject}");
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        var runs = doc.RootElement.GetProperty("runs");
        Assert.True(runs.GetArrayLength() >= 3);

        // Verify each run's data
        var runMap = new Dictionary<string, JsonElement>();
        foreach (var run in runs.EnumerateArray())
        {
            var id = run.GetProperty("runId").GetString()!;
            runMap[id] = run;
        }

        // Run A: state with stateId matching snapshotA
        Assert.True(runMap.ContainsKey(runIdA));
        Assert.NotEqual(JsonValueKind.Null, runMap[runIdA].GetProperty("state").ValueKind);
        Assert.Equal(snapshotA.StateId, runMap[runIdA].GetProperty("state").GetProperty("stateId").GetString());

        // Run B: state with stateId matching snapshotB
        Assert.True(runMap.ContainsKey(runIdB));
        Assert.NotEqual(JsonValueKind.Null, runMap[runIdB].GetProperty("state").ValueKind);
        Assert.Equal(snapshotB.StateId, runMap[runIdB].GetProperty("state").GetProperty("stateId").GetString());

        // Run C: no state
        Assert.True(runMap.ContainsKey(runIdC));
        Assert.Equal(JsonValueKind.Null, runMap[runIdC].GetProperty("state").ValueKind);
    }

    // ── Scenario 4: Reinstatement failure modes produce actionable messages (INTG-03) ──

    [Fact]
    public void ReinstateFailureModes_ProduceActionableMessages()
    {
        // Build snapshot with 3 parameters
        var snapshot = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "height", DisplayName = "Height",
                Type = DesignStateParameterType.Number, NumberValue = 75.0,
            },
            new DesignStateParameter
            {
                ParameterId = "isActive", DisplayName = "Is Active",
                Type = DesignStateParameterType.Boolean, BooleanValue = true,
            },
            new DesignStateParameter
            {
                ParameterId = "floors", DisplayName = "Floors",
                Type = DesignStateParameterType.Integer, IntegerValue = 5,
            });

        // Build targets that trigger failures
        var targets = new[]
        {
            // height → MissingTarget
            new ResolvedTarget("height", TargetResolutionStatus.Missing, DesignStateParameterType.Number, null, null),
            // isActive → TypeMismatch (target is Number, but param is Boolean)
            new ResolvedTarget("isActive", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, null, null),
            // floors → OutOfRange (domain max=3, value=5)
            new ResolvedTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Integer, 1, 3),
        };

        var service = new DesignStateReinstatementService();
        var result = service.Validate(snapshot, targets, lastAppliedStateId: null);

        // Should abort (atomic abort per D-06)
        Assert.True(result.Aborted);

        // Verify each report
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var isActiveReport = result.Reports.Single(r => r.ParameterId == "isActive");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");

        Assert.Equal(ReinstatementStatus.MissingTarget, heightReport.Status);
        Assert.Equal(ReinstatementStatus.TypeMismatch, isActiveReport.Status);
        // floors: IntegerValue=5, domain max=3 → OutOfRange
        Assert.Equal(ReinstatementStatus.OutOfRange, floorsReport.Status);

        // Verify ErrorMessageTemplates produce actionable messages for each failure
        var heightMsg = ErrorMessageTemplates.ReinstatementBlocked(
            heightReport.ParameterId, heightReport.Status, heightReport.Detail ?? "");
        Assert.Contains("height", heightMsg);
        Assert.Contains(": ", heightMsg);
        Assert.EndsWith(".", heightMsg);

        var isActiveMsg = ErrorMessageTemplates.ReinstatementBlocked(
            isActiveReport.ParameterId, isActiveReport.Status, isActiveReport.Detail ?? "");
        Assert.Contains("isActive", isActiveMsg);
        Assert.Contains(": ", isActiveMsg);
        Assert.EndsWith(".", isActiveMsg);

        var floorsMsg = ErrorMessageTemplates.ReinstatementBlocked(
            floorsReport.ParameterId, floorsReport.Status, floorsReport.Detail ?? "");
        Assert.Contains("floors", floorsMsg);
        Assert.Contains(": ", floorsMsg);
        Assert.EndsWith(".", floorsMsg);
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────

    private static DesignStateSnapshot CreateSnapshot(params DesignStateParameter[] parameters)
    {
        var snapshot = new DesignStateSnapshot
        {
            StateId = $"e2e-state-{string.Join("-", parameters.Select(p => p.ParameterId))}",
            CapturedAtUtc = new DateTimeOffset(2026, 1, 15, 10, 0, 0, TimeSpan.Zero),
        };

        foreach (var p in parameters)
        {
            snapshot.Parameters.Add(p);
        }

        return snapshot;
    }
}
