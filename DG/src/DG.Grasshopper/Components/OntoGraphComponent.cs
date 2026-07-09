#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;
using CoreOntologyClass = DG.Core.Models.OntologyClass;
using CoreOntologyProperty = DG.Core.Models.OntologyProperty;

namespace DG.Grasshopper.Components;

public sealed class OntoGraphComponent : GH_Component
{
    private readonly IOntoGraphRepository _repository = new Neo4jOntoGraphRepository();
    private Task<IReadOnlyList<CoreOntologyClass>>? _classesTask;
    private Task<IReadOnlyList<CoreOntologyProperty>>? _objPropertiesTask;
    private Task<IReadOnlyList<CoreOntologyProperty>>? _dataPropertiesTask;
    private CancellationTokenSource? _loadCts;
    private string _activeRequestKey = string.Empty;
    private bool _refreshLatched;
    private List<global::DG.OntologyClass> _latestClasses = new();
    private List<global::DG.OntologyProperty> _latestObjProperties = new();
    private List<global::DG.OntologyProperty> _latestDataProperties = new();
    private string _latestStatus = "Idle";

    public OntoGraphComponent()
        : base("ONTOGRAPH", "ONTOGRAPH",
            "Load Classes, ObjProperties, and DataProperties from the OntoGraph layer.",
            DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    public override Guid ComponentGuid => new("F8C6A4B2-1E3D-4F5A-8C7B-9D0E1F2A3B4C");

    protected override Bitmap Icon => DgIcons.OntoGraph24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Ontograph", "Ontograph",
            "Ontograph layer handle from GRAPH DECONSTRUCT", GH_ParamAccess.item);
        pManager.AddBooleanParameter("Refresh", "Refresh",
            "Set true to load ontology data from OntoGraph", GH_ParamAccess.item, true);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Class", "Class",
            "List of OntologyClass objects from the OntoGraph layer", GH_ParamAccess.list);
        pManager.AddGenericParameter("ObjProperties", "ObjProperties",
            "List of OntologyProperty objects (object properties)", GH_ParamAccess.list);
        pManager.AddGenericParameter("DataProperties", "DataProperties",
            "List of OntologyProperty objects (data properties)", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? handleInput = null;
        var refresh = true;
        if (!da.GetData(0, ref handleInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.HandleTypeUnwrapped("ONTOGRAPH", "Ontograph"));
            SetEmptyOutputs(da, "No input.");
            return;
        }

        var handle = GhCastingHelpers.Unwrap<global::DG.OntographHandle>(handleInput);
        if (handle is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.HandleTypeUnwrapped("ONTOGRAPH", "Ontograph"));
            SetEmptyOutputs(da, "Invalid handle.");
            return;
        }

        da.GetData(1, ref refresh);
        if (!refresh)
        {
            CancelPendingLoad();
            _refreshLatched = false;
            _latestStatus = "Idle";
            Message = "Idle";
            SetOutputs(da);
            return;
        }

        if (!handle.ConnectionInfo.IsConnected)
        {
            CancelPendingLoad();
            _latestClasses = new List<global::DG.OntologyClass>();
            _latestObjProperties = new List<global::DG.OntologyProperty>();
            _latestDataProperties = new List<global::DG.OntologyProperty>();
            _latestStatus = "Connection is not connected.";
            Message = "No connection";
            SetOutputs(da);
            return;
        }

        var connection = handle.ConnectionInfo;
        var requestKey = BuildRequestKey(connection);
        var connectionChanged = !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal);
        var refreshPressed = refresh && !_refreshLatched;
        _refreshLatched = refresh;

        if (_classesTask is null || _objPropertiesTask is null || _dataPropertiesTask is null
            || connectionChanged || refreshPressed)
        {
            StartLoad(connection, requestKey);
        }

        if (_classesTask is { IsCompletedSuccessfully: true }
            && _objPropertiesTask is { IsCompletedSuccessfully: true }
            && _dataPropertiesTask is { IsCompletedSuccessfully: true })
        {
            _latestClasses = _classesTask.Result.Select(ToPublicClass).ToList();
            _latestObjProperties = _objPropertiesTask.Result.Select(ToPublicProperty).ToList();
            _latestDataProperties = _dataPropertiesTask.Result.Select(ToPublicProperty).ToList();
            _latestStatus = $"Loaded {_latestClasses.Count} classes, {_latestObjProperties.Count} obj props, {_latestDataProperties.Count} data props.";
            Message = $"{_latestClasses.Count} classes";
        }
        else if (_classesTask is { IsFaulted: true }
              || _objPropertiesTask is { IsFaulted: true }
              || _dataPropertiesTask is { IsFaulted: true })
        {
            var error = _classesTask?.Exception?.GetBaseException().Message
                     ?? _objPropertiesTask?.Exception?.GetBaseException().Message
                     ?? _dataPropertiesTask?.Exception?.GetBaseException().Message
                     ?? "Failed to load OntoGraph data.";
            _latestClasses = new List<global::DG.OntologyClass>();
            _latestObjProperties = new List<global::DG.OntologyProperty>();
            _latestDataProperties = new List<global::DG.OntologyProperty>();
            _latestStatus = error;
            Message = "Load failed";
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, _latestStatus);
        }
        else if (_classesTask is { IsCanceled: true })
        {
            _latestStatus = "Load canceled.";
            Message = "Canceled";
        }
        else
        {
            _latestStatus = "Loading OntoGraph data...";
            Message = "Loading...";
        }

        SetOutputs(da);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingLoad();
        base.RemovedFromDocument(document);
    }

    private void StartLoad(ConnectionInfo connection, string requestKey)
    {
        CancelPendingLoad();

        _activeRequestKey = requestKey;
        _loadCts = new CancellationTokenSource();
        var ct = _loadCts.Token;
        _classesTask = _repository.GetClassesAsync(connection, ct);
        _objPropertiesTask = _repository.GetObjPropertiesAsync(connection, ct);
        _dataPropertiesTask = _repository.GetDataPropertiesAsync(connection, ct);

        _ = Task.WhenAll(_classesTask, _objPropertiesTask, _dataPropertiesTask).ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private void CancelPendingLoad()
    {
        try
        {
            _loadCts?.Cancel();
        }
        catch
        {
            // no-op
        }
        finally
        {
            _loadCts?.Dispose();
            _loadCts = null;
            _classesTask = null;
            _objPropertiesTask = null;
            _dataPropertiesTask = null;
            _activeRequestKey = string.Empty;
        }
    }

    private static string BuildRequestKey(ConnectionInfo connection)
    {
        return $"{connection.Uri}|{connection.User}|{connection.Password}|{connection.Database}|{connection.Project}";
    }

    private void SetOutputs(IGH_DataAccess da)
    {
        da.SetDataList(0, _latestClasses);
        da.SetDataList(1, _latestObjProperties);
        da.SetDataList(2, _latestDataProperties);
        if (!string.IsNullOrWhiteSpace(_latestStatus))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, _latestStatus);
        }
    }

    private void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        _latestClasses = new List<global::DG.OntologyClass>();
        _latestObjProperties = new List<global::DG.OntologyProperty>();
        _latestDataProperties = new List<global::DG.OntologyProperty>();
        _latestStatus = status;
        Message = status;
        SetOutputs(da);
    }

    private static global::DG.OntologyClass ToPublicClass(CoreOntologyClass c)
    {
        return new global::DG.OntologyClass
        {
            Iri = c.Iri,
            Label = c.Label,
        };
    }

    private static global::DG.OntologyProperty ToPublicProperty(CoreOntologyProperty p)
    {
        return new global::DG.OntologyProperty
        {
            Iri = p.Iri,
            Label = p.Label,
        };
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class OntoGraphComponent
{
}
#endif
