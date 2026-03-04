#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using Grasshopper.Kernel;
using System.Drawing;
using CoreRule = DG.Core.Models.Rule;

namespace DG.Grasshopper.Components;

public sealed class MetagraphComponent : GH_Component
{
    private readonly IRuleRepository _ruleRepository = new Neo4jRuleRepository();
    private Task<IReadOnlyList<CoreRule>>? _loadTask;
    private CancellationTokenSource? _loadCts;
    private string _activeRequestKey = string.Empty;
    private bool _refreshLatched;
    private List<global::DG.Rule> _latestRules = new();
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

        var connection = GhCastingHelpers.Unwrap<ConnectionInfo>(connectionInput);
        if (connection is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Connection input.");
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

        if (_loadTask is null || connectionChanged || refreshPressed)
        {
            StartLoad(connection, requestKey);
        }

        if (_loadTask is { IsCompletedSuccessfully: true })
        {
            _latestRules = _loadTask.Result.Select(ToPublicRule).ToList();
            _latestStatus = $"Loaded {_latestRules.Count} rules.";
            Message = $"{_latestRules.Count} rules";
        }
        else if (_loadTask is { IsFaulted: true })
        {
            _latestRules = new List<global::DG.Rule>();
            var error = _loadTask.Exception?.GetBaseException().Message ?? "Failed to load rules.";
            _latestStatus = error;
            Message = "Load failed";
        }
        else if (_loadTask is { IsCanceled: true })
        {
            _latestStatus = "Load canceled.";
            Message = "Canceled";
        }
        else
        {
            _latestStatus = "Loading rules from Metagraph...";
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
        _latestStatus = "Loading rules from Metagraph...";
        _loadCts = new CancellationTokenSource();
        _loadTask = _ruleRepository.GetRulesAsync(connection, _loadCts.Token);

        _ = _loadTask.ContinueWith(
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
        if (!string.IsNullOrWhiteSpace(_latestStatus))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, _latestStatus);
        }
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
