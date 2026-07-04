#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;
using CoreRule = DG.Core.Models.Rule;

namespace DG.Grasshopper.Components;

public sealed class MetagraphComponent : GH_Component
{
    private readonly IRuleRepository _ruleRepository = new Neo4jRuleRepository();
    private CancellationTokenSource? _loadCts;
    private string _activeRequestKey = string.Empty;
    private bool _refreshLatched;
    private List<global::DG.Rule> _latestRules = new();
    private List<global::DG.OntologyClass> _latestObjects = new();
    private Task<IReadOnlyList<CoreRule>>? _loadTask;
    private Task<IReadOnlyList<DG.Core.Models.OntologyClass>>? _objectsLoadTask;
    private string _latestStatus = "Idle";

    public MetagraphComponent()
        : base("METAGRAPH", "METAGRAPH", "Load design rules from Neo4j Metagraph.", DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("6ED440FB-EF12-49D1-8969-74A2B0E72360");

    protected override Bitmap Icon => DgIcons.Metagraph24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Connection", "Connection", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddBooleanParameter("Refresh", "Refresh", "Set true to fetch rules", GH_ParamAccess.item, true);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Rules", "Rules", "List of DG.Rule objects", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleName", "RuleName", "Rule names", GH_ParamAccess.list);
        pManager.AddIntegerParameter("Count", "Count", "Number of rules", GH_ParamAccess.item);
        pManager.AddGenericParameter("Objects", "Objects", "List of OntologyClass objects referenced by rules", GH_ParamAccess.list);
        pManager.AddTextParameter("ObjectName", "ObjectName", "Object names (labels)", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? connectionInput = null;
        var refresh = true;
        if (!da.GetData(0, ref connectionInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Connection input is required.");
            return;
        }

        var handle = GhCastingHelpers.Unwrap<global::DG.MetagraphHandle>(connectionInput);
        if (handle is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.HandleTypeUnwrapped("METAGRAPH", "MetagraphHandle"));
            return;
        }

        var connection = handle.ConnectionInfo;

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

        if (!connection.IsConnected)
        {
            CancelPendingLoad();
            _latestRules = new List<global::DG.Rule>();
            _latestStatus = "Connection is not connected.";
            Message = "No connection";
            SetOutputs(da);
            return;
        }

        var requestKey = BuildRequestKey(connection);
        var connectionChanged = !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal);
        var refreshPressed = refresh && !_refreshLatched;
        _refreshLatched = refresh;

        if (_loadTask is null || _objectsLoadTask is null || connectionChanged || refreshPressed)
        {
            StartLoad(connection, requestKey);
        }

        if (_loadTask is { IsCompletedSuccessfully: true } && _objectsLoadTask is { IsCompletedSuccessfully: true })
        {
            _latestRules = _loadTask.Result.Select(ToPublicRule).ToList();
            _latestObjects = _objectsLoadTask.Result.Select<DG.Core.Models.OntologyClass, global::DG.OntologyClass>(ToPublicOntologyClass).ToList();
            _latestStatus = $"Loaded {_latestRules.Count} rules, {_latestObjects.Count} objects.";
            Message = $"{_latestRules.Count} rules";
        }
        else if (_loadTask is { IsFaulted: true } || _objectsLoadTask is { IsFaulted: true })
        {
            var errors = new List<string>();
            if (_loadTask is { IsFaulted: true })
                errors.Add(_loadTask.Exception?.GetBaseException().Message ?? "Rules load failed");
            if (_objectsLoadTask is { IsFaulted: true })
                errors.Add(_objectsLoadTask.Exception?.GetBaseException().Message ?? "Objects load failed");
            _latestRules = new List<global::DG.Rule>();
            _latestObjects = new List<global::DG.OntologyClass>();
            _latestStatus = string.Join("; ", errors);
            Message = "Load failed";
        }
        else if (_loadTask is { IsCanceled: true } || _objectsLoadTask is { IsCanceled: true })
        {
            _latestStatus = "Load canceled.";
            Message = "Canceled";
        }
        else
        {
            _latestStatus = "Loading rules and objects from Metagraph...";
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
        _latestStatus = "Loading rules and objects from Metagraph...";
        _loadCts = new CancellationTokenSource();
        var ct = _loadCts.Token;
        _loadTask = _ruleRepository.GetRulesAsync(connection, ct);
        _objectsLoadTask = _ruleRepository.GetObjectsAsync(connection, ct);

        _ = Task.WhenAll(_loadTask, _objectsLoadTask).ContinueWith(
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
            _loadTask = null;
            _objectsLoadTask = null;
            _activeRequestKey = string.Empty;
        }
    }

    private static string BuildRequestKey(ConnectionInfo connection)
    {
        return $"{connection.Uri}|{connection.User}|{connection.Password}|{connection.Database}|{connection.Project}";
    }

    private void SetOutputs(IGH_DataAccess da)
    {
        da.SetDataList(0, _latestRules);
        da.SetDataList(1, _latestRules.Select(rule => string.IsNullOrWhiteSpace(rule.Name) ? rule.Id : rule.Name));
        da.SetData(2, _latestRules.Count);
        da.SetDataList(3, _latestObjects);
        da.SetDataList(4, _latestObjects.Select(obj => string.IsNullOrWhiteSpace(obj.Label) ? obj.Iri : obj.Label));
        if (!string.IsNullOrWhiteSpace(_latestStatus))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, _latestStatus);
        }
    }

    private static global::DG.OntologyClass ToPublicOntologyClass(DG.Core.Models.OntologyClass obj)
    {
        return new global::DG.OntologyClass
        {
            Iri = obj.Iri,
            Label = obj.Label,
        };
    }

    private static global::DG.Rule ToPublicRule(CoreRule rule)
    {
        var publicRule = new global::DG.Rule
        {
            Id = rule.Id,
            Name = rule.Name,
            Description = rule.Description,
            Kind = rule.Kind,
            Text = rule.Text,
            Swrl = rule.Swrl,
            Project = rule.Project,
            Graph = rule.Graph,
        };

        foreach (var atom in rule.BodyAtoms)
        {
            publicRule.BodyAtoms.Add(atom);
        }

        foreach (var atom in rule.HeadAtoms)
        {
            publicRule.HeadAtoms.Add(atom);
        }

        foreach (var variable in rule.Variables)
        {
            publicRule.Variables.Add(new global::DG.Variable
            {
                Name = variable.Name,
                InferredDatatype = variable.InferredDatatype,
                Kind = variable.Kind,
            });
        }

        return publicRule;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class MetagraphComponent
{
}
#endif
