#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ValidationGraphComponent : GH_Component
{
    private readonly IValidGraphRepository _repository = new Neo4jValidGraphRepository();
    private Task<ValidGraphQueryResult>? _queryTask;
    private CancellationTokenSource? _queryCts;
    private string _activeRequestKey = string.Empty;
    private bool _refreshLatched;
    private List<global::DG.RunInfo> _latestRuns = new();
    private List<IReadOnlyList<bool>> _latestStatusData = new();
    private List<global::DG.DesignState> _latestDesignStates = new();
    private string _latestStatus = "Idle";

    public ValidationGraphComponent()
        : base("VALIDATION GRAPH", "VALGRAPH",
            "Load validation runs, status, and design states from the ValidGraph layer.",
            DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    public override Guid ComponentGuid => new("95fc9d32-307e-41fd-a158-bfae49a3dc2a");

    protected override Bitmap Icon => DgIcons.ValidationGraph24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("ValidGraph", "ValidGraph",
            "ValidGraph layer handle from GRAPH DECONSTRUCT", GH_ParamAccess.item);
        pManager.AddBooleanParameter("Refresh", "Refresh",
            "Set true to load validation data from ValidGraph", GH_ParamAccess.item, true);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Run", "Run", "List of RunInfo objects — validation run metadata.", GH_ParamAccess.list);
        pManager.AddGenericParameter("Status", "Status", "Per-ObjState Boolean status lists, index-matched to Run.", GH_ParamAccess.list);
        pManager.AddGenericParameter("DesignState", "DesignState", "List of DesignState objects — deduplicated by StateId.", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? handleInput = null;
        if (!da.GetData(0, ref handleInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "ValidGraph input is required.");
            SetEmptyOutputs(da, "No ValidGraph handle.");
            return;
        }

        var handle = GhCastingHelpers.Unwrap<global::DG.ValidGraphHandle>(handleInput);
        if (handle is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.HandleTypeUnwrapped("VALIDATION GRAPH", "ValidGraphHandle"));
            SetEmptyOutputs(da, "Invalid handle.");
            return;
        }

        var connection = handle.ConnectionInfo;

        var refresh = true;
        da.GetData(1, ref refresh);

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
            _latestRuns = new List<global::DG.RunInfo>();
            _latestStatusData = new List<IReadOnlyList<bool>>();
            _latestDesignStates = new List<global::DG.DesignState>();
            _latestStatus = "Connection is not connected.";
            Message = "No connection";
            SetOutputs(da);
            return;
        }

        var requestKey = BuildRequestKey(connection);
        var connectionChanged = !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal);
        var refreshPressed = refresh && !_refreshLatched;
        _refreshLatched = refresh;

        if (_queryTask is null || connectionChanged || refreshPressed)
        {
            StartLoad(connection, requestKey);
        }

        if (_queryTask is { IsCompletedSuccessfully: true })
        {
            var result = _queryTask.Result;
            _latestRuns = result.Runs.Select(ToPublicRunInfo).ToList();
            _latestStatusData = result.StatusList.ToList();
            _latestDesignStates = result.DesignStates.Select(ToPublicDesignState).ToList();
            _latestStatus = $"Loaded {result.Runs.Count} runs, {result.DesignStates.Count} design states.";
            Message = $"{result.Runs.Count} runs";
        }
        else if (_queryTask is { IsFaulted: true })
        {
            _latestRuns = new List<global::DG.RunInfo>();
            _latestStatusData = new List<IReadOnlyList<bool>>();
            _latestDesignStates = new List<global::DG.DesignState>();
            var error = _queryTask.Exception?.GetBaseException().Message ?? "Failed to load validation data.";
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
            _latestStatus = "Loading validation runs from ValidGraph...";
            Message = "Loading...";
        }

        SetOutputs(da);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingQuery();
        base.RemovedFromDocument(document);
    }

    private void StartLoad(ConnectionInfo connection, string requestKey)
    {
        CancelPendingQuery();

        _activeRequestKey = requestKey;
        _latestStatus = "Loading validation runs from ValidGraph...";
        _queryCts = new CancellationTokenSource();
        var ct = _queryCts.Token;
        _queryTask = _repository.GetRunsAsync(connection, ct);

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

    private static string BuildRequestKey(ConnectionInfo connection)
    {
        return $"{connection.Uri}|{connection.User}|{connection.Password}|{connection.Database}|{connection.Project}";
    }

    private void SetOutputs(IGH_DataAccess da)
    {
        da.SetDataList(0, _latestRuns);
        da.SetDataList(1, _latestStatusData);
        da.SetDataList(2, _latestDesignStates);

        if (!string.IsNullOrWhiteSpace(_latestStatus))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, _latestStatus);
        }
    }

    private static void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        da.SetDataList(0, new List<global::DG.RunInfo>());
        da.SetDataList(1, new List<IReadOnlyList<bool>>());
        da.SetDataList(2, new List<global::DG.DesignState>());
        da.SetData(0, status);
    }

    private static global::DG.RunInfo ToPublicRunInfo(DG.Core.Data.RunInfo runInfo)
    {
        return new global::DG.RunInfo
        {
            RunId = runInfo.RunId,
            Project = runInfo.Project,
            CapturedAtUtc = runInfo.CapturedAtUtc,
            RuleIds = runInfo.RuleIds,
            StateId = runInfo.StateId,
        };
    }

    private static global::DG.DesignState ToPublicDesignState(DG.Core.Models.DesignState state)
    {
        var publicState = new global::DG.DesignState
        {
            StateId = state.StateId,
            CapturedAtUtc = state.CapturedAtUtc,
        };

        foreach (var os in state.ObjStates)
        {
            publicState.ObjStates.Add(ToPublicObjState(os));
        }

        foreach (var ps in state.ParamStates)
        {
            publicState.ParamStates.Add(ToPublicParamState(ps));
        }

        foreach (var ps in state.PropStates)
        {
            publicState.PropStates.Add(ToPublicPropState(ps));
        }

        return publicState;
    }

    private static global::DG.ObjState ToPublicObjState(DG.Core.Models.ObjState objState)
    {
        return new global::DG.ObjState
        {
            StateId = objState.StateId,
            ObjectRef = objState.ObjectRef,
            Geometry = objState.Geometry,
            Label = objState.Label,
            CapturedAtUtc = objState.CapturedAtUtc,
        };
    }

    private static global::DG.ParamState ToPublicParamState(DG.Core.Models.ParamState paramState)
    {
        var publicParamState = new global::DG.ParamState
        {
            StateId = paramState.StateId,
            CapturedAtUtc = paramState.CapturedAtUtc,
        };

        foreach (var p in paramState.Parameters)
        {
            publicParamState.Parameters.Add(p);
        }

        return publicParamState;
    }

    private static global::DG.PropState ToPublicPropState(DG.Core.Models.PropState propState)
    {
        return new global::DG.PropState
        {
            StateId = propState.StateId,
            RuleIri = propState.RuleIri,
            DataPropertyIri = propState.DataPropertyIri,
            PropValue = propState.PropValue,
        };
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ValidationGraphComponent
{
}
#endif
