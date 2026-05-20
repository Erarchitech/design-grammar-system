#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

/// <summary>
/// VALIDATION RUNS component. Queries Neo4j for validation runs with optional Rule and State filters.
/// Outputs: Runs (ValidationRunQueryResult list), Results (formatted strings), States (DesignStateSnapshot list).
/// </summary>
public sealed class ValidationRunsComponent : GH_Component
{
    private readonly ValidationRunsQueryService _queryService = new();
    private Task<IReadOnlyList<ValidationRunQueryResult>>? _queryTask;
    private CancellationTokenSource? _queryCts;
    private string _activeRequestKey = string.Empty;
    private bool _refreshLatched;
    private List<ValidationRunQueryResult> _latestRuns = new();
    private string _latestStatus = "Idle";

    public ValidationRunsComponent()
        : base(
            "VALIDATION RUNS",
            "VALIDRUNS",
            "Query validation runs from Neo4j with optional Rule and State filters.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("A7F2C3E1-B849-4D6A-9F0E-3C2D1E5B8A94");

    protected override Bitmap Icon => DgIcons.ValidationRuns24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Connection", "Connection", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddGenericParameter("Rule", "Rule", "Optional DG.Rule to filter runs by rule ID. Leave unconnected for all runs.", GH_ParamAccess.item);
        pManager[1].Optional = true;
        pManager.AddGenericParameter("State", "State", "Optional DG.DesignStateSnapshot to filter runs by state ID. Leave unconnected for all runs.", GH_ParamAccess.item);
        pManager[2].Optional = true;
        pManager.AddBooleanParameter("Refresh", "Refresh", "Set true to fetch validation runs", GH_ParamAccess.item, true);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Runs", "Runs", "List of ValidationRunQueryResult objects — full run records.", GH_ParamAccess.list);
        pManager.AddTextParameter("Results", "Results", "Per-run result lines. Format: '{ruleId}:{passed}' per rule per run.", GH_ParamAccess.list);
        pManager.AddGenericParameter("States", "States", "Deserialized DesignStateSnapshot objects for runs that have an attached state. Empty when no states are stored.", GH_ParamAccess.list);
        pManager.AddTextParameter("Status", "Status", "Query status message.", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? connectionInput = null;
        if (!da.GetData(0, ref connectionInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Connection input is required.");
            SetEmptyOutputs(da, "No connection.");
            return;
        }

        var connection = GhCastingHelpers.Unwrap<ConnectionInfo>(connectionInput);
        if (connection is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Connection input.");
            SetEmptyOutputs(da, "Invalid connection.");
            return;
        }

        object? ruleInput = null;
        da.GetData(1, ref ruleInput);
        var ruleFilter = GhCastingHelpers.TryRule(ruleInput);
        var ruleId = ruleFilter?.Id;

        object? stateInput = null;
        da.GetData(2, ref stateInput);
        var stateFilter = GhCastingHelpers.Unwrap<DesignStateSnapshot>(stateInput)
                          ?? GhCastingHelpers.Unwrap<global::DG.DesignStateSnapshot>(stateInput);
        var stateId = stateFilter?.StateId;

        var refresh = true;
        da.GetData(3, ref refresh);

        if (!refresh)
        {
            CancelPendingQuery();
            _refreshLatched = false;
            _latestStatus = "Idle";
            Message = "Idle";
            SetOutputs(da);
            return;
        }

        if (!connection.IsConnected)
        {
            CancelPendingQuery();
            _latestRuns = new List<ValidationRunQueryResult>();
            _latestStatus = "Connection is not connected.";
            Message = "No connection";
            SetOutputs(da);
            return;
        }

        var requestKey = BuildRequestKey(connection, ruleId, stateId);
        var connectionChanged = !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal);
        var refreshPressed = refresh && !_refreshLatched;
        _refreshLatched = refresh;

        if (_queryTask is null || connectionChanged || refreshPressed)
        {
            StartQuery(connection, ruleId, stateId, requestKey);
        }

        if (_queryTask is { IsCompletedSuccessfully: true })
        {
            _latestRuns = _queryTask.Result.ToList();
            _latestStatus = $"Loaded {_latestRuns.Count} runs.";
            Message = $"{_latestRuns.Count} runs";
        }
        else if (_queryTask is { IsFaulted: true })
        {
            _latestRuns = new List<ValidationRunQueryResult>();
            var error = _queryTask.Exception?.GetBaseException().Message ?? "Failed to load validation runs.";
            _latestStatus = error;
            Message = "Load failed";
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, _latestStatus);
        }
        else if (_queryTask is { IsCanceled: true })
        {
            _latestStatus = "Query canceled.";
            Message = "Canceled";
        }
        else
        {
            _latestStatus = "Loading validation runs...";
            Message = "Loading...";
        }

        SetOutputs(da);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingQuery();
        base.RemovedFromDocument(document);
    }

    private void StartQuery(ConnectionInfo connection, string? ruleId, string? stateId, string requestKey)
    {
        CancelPendingQuery();

        _activeRequestKey = requestKey;
        _latestStatus = "Loading validation runs...";
        _queryCts = new CancellationTokenSource();
        _queryTask = _queryService.QueryAsync(connection, ruleId, stateId, _queryCts.Token);

        _ = _queryTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private void CancelPendingQuery()
    {
        try
        {
            _queryCts?.Cancel();
        }
        catch
        {
            // no-op: cancellation is best-effort.
        }
        finally
        {
            _queryCts?.Dispose();
            _queryCts = null;
            _queryTask = null;
            _activeRequestKey = string.Empty;
        }
    }

    private static string BuildRequestKey(ConnectionInfo connection, string? ruleId, string? stateId)
    {
        return $"{connection.Uri}|{connection.User}|{connection.Password}|{connection.Database}|{connection.Project}|rule:{ruleId ?? string.Empty}|state:{stateId ?? string.Empty}";
    }

    private void SetOutputs(IGH_DataAccess da)
    {
        da.SetDataList(0, _latestRuns);
        da.SetDataList(1, BuildResultLines(_latestRuns));
        da.SetDataList(2, _latestRuns.Where(run => run.State is not null).Select(run => run.State).ToList());
        da.SetData(3, _latestStatus);

        if (!string.IsNullOrWhiteSpace(_latestStatus))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, _latestStatus);
        }
    }

    private static void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        da.SetDataList(0, new List<ValidationRunQueryResult>());
        da.SetDataList(1, new List<string>());
        da.SetDataList(2, new List<DesignStateSnapshot>());
        da.SetData(3, status);
    }

    private static IReadOnlyList<string> BuildResultLines(IReadOnlyList<ValidationRunQueryResult> runs)
    {
        // Format: "{runId}|{ruleId}:{passed}" — one line per rule per run.
        var lines = new List<string>();
        foreach (var run in runs)
        {
            foreach (var resultLine in run.Results)
            {
                lines.Add($"{run.RunId}|{resultLine}");
            }
        }

        return lines;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ValidationRunsComponent
{
}
#endif
