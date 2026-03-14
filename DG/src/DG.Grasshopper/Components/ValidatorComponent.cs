#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Validation;
using DG.Grasshopper.Validation;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent : GH_Component
{
    private readonly RuleEvaluator _ruleEvaluator = new();

    public ValidatorComponent()
        : base("VALIDATOR", "VALIDATOR", "Validate parametric state against DG rules.", DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("C202D04A-9CC2-4CD1-9F47-C77D4093D447");

    protected override Bitmap Icon => DgIcons.Validator24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Rules", "Rules", "Rule list from METAGRAPH", GH_ParamAccess.list);
        pManager.AddGenericParameter("Variables", "Variables", "Binding rows from CLASSIFICATOR", GH_ParamAccess.list);
        pManager.AddBooleanParameter("Run", "Run", "Set true to validate", GH_ParamAccess.item, false);
        pManager.AddBooleanParameter("SendRules", "SendRules", "Set true to send validation geometry and results to DG backend for Speckle publication", GH_ParamAccess.item, false);
        pManager.AddTextParameter("DataServiceUrl", "DataServiceUrl", "DG data-service base URL", GH_ParamAccess.item, "http://localhost:8000");
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddBooleanParameter("Pass", "Pass", "Per-rule pass/no pass", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleName", "RuleName", "Rule names", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleDescription", "RuleDescription", "Rule descriptions", GH_ParamAccess.list);
        pManager.AddTextParameter("Report", "Report", "Per-rule report lines", GH_ParamAccess.list);
        pManager.AddTextParameter("FailingBindings", "FailingBindings", "Failing bindings in format: b(building32): h(83), w(54)", GH_ParamAccess.list);
        pManager.AddTextParameter("PublishStatus", "PublishStatus", "Speckle publish status", GH_ParamAccess.item);
        pManager.AddTextParameter("ValidationRunId", "ValidationRunId", "Validation run identifier returned by DG backend", GH_ParamAccess.item);
        pManager.AddTextParameter("ModelViewerUrl", "ModelViewerUrl", "Model Viewer URL returned by DG backend", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var run = false;
        da.GetData(2, ref run);
        var sendRules = false;
        da.GetData(3, ref sendRules);
        var dataServiceUrl = "http://localhost:8000";
        da.GetData(4, ref dataServiceUrl);
        if (!run)
        {
            Message = "Idle";
            return;
        }

        var ruleInputs = new List<object>();
        var bindingInputs = new List<object>();
        if (!da.GetDataList(0, ruleInputs))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Rules input is required.");
            return;
        }

        if (!da.GetDataList(1, bindingInputs))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Variables (bindings) input is required.");
            return;
        }

        var rules = ruleInputs
            .Select(GhCastingHelpers.TryRule)
            .Where(rule => rule is not null)
            .Select(rule => rule!)
            .ToList();

        var bindings = bindingInputs
            .Select(GhCastingHelpers.TryBindingRow)
            .Where(binding => binding is not null)
            .Select(binding => binding!)
            .ToList();

        if (rules.Count == 0)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No rules to validate.");
            return;
        }

        var results = _ruleEvaluator.EvaluateRules(rules, bindings);
        var pass = results.Select(result => result.Passed).ToList();
        var names = results.Select(result => result.RuleName).ToList();
        var descriptions = results.Select(result => result.RuleDescription).ToList();
        var reports = results.Select(ValidationReportFormatter.ToReportLine).ToList();
        var ruleById = rules
            .GroupBy(rule => rule.Id)
            .ToDictionary(group => group.Key, group => group.First(), StringComparer.Ordinal);
        var failing = new List<string>();
        foreach (var result in results)
        {
            if (!ruleById.TryGetValue(result.RuleId, out var rule))
            {
                continue;
            }

            foreach (var binding in result.FailingBindings)
            {
                failing.Add(FailingBindingFormatter.Format(rule, binding));
            }
        }

        var publishStatus = sendRules ? "Pending" : "Not requested";
        var validationRunId = string.Empty;
        var modelViewerUrl = string.Empty;
        if (sendRules)
        {
            try
            {
                var response = ValidationPublishClient.Publish(rules, results, bindings, dataServiceUrl);
                publishStatus = string.IsNullOrWhiteSpace(response.Status) ? "published" : response.Status;
                validationRunId = response.RunId;
                modelViewerUrl = response.ModelViewerUrl;
            }
            catch (Exception ex)
            {
                publishStatus = $"Publish failed: {ex.Message}";
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, publishStatus);
            }
        }

        da.SetDataList(0, pass);
        da.SetDataList(1, names);
        da.SetDataList(2, descriptions);
        da.SetDataList(3, reports);
        da.SetDataList(4, failing);
        da.SetData(5, publishStatus);
        da.SetData(6, validationRunId);
        da.SetData(7, modelViewerUrl);
        Message = sendRules
            ? $"{pass.Count(value => value)} / {pass.Count} pass | {publishStatus}"
            : $"{pass.Count(value => value)} / {pass.Count} pass";
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent
{
}
#endif
