#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Validation;
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
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddBooleanParameter("Pass", "Pass", "Per-rule pass/no pass", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleName", "RuleName", "Rule names", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleDescription", "RuleDescription", "Rule descriptions", GH_ParamAccess.list);
        pManager.AddTextParameter("Report", "Report", "Per-rule report lines", GH_ParamAccess.list);
        pManager.AddGenericParameter("FailingBindings", "FailingBindings", "Failing bindings as dictionaries: variable name -> value", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var run = false;
        da.GetData(2, ref run);
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
        var failing = results
            .SelectMany(ToFailingBindingDictionaries)
            .ToList();

        da.SetDataList(0, pass);
        da.SetDataList(1, names);
        da.SetDataList(2, descriptions);
        da.SetDataList(3, reports);
        da.SetDataList(4, failing);
        Message = $"{pass.Count(value => value)} / {pass.Count} pass";
    }

    private static IEnumerable<Dictionary<string, object?>> ToFailingBindingDictionaries(RuleEvaluationResult result)
    {
        foreach (var binding in result.FailingBindings)
        {
            var output = new Dictionary<string, object?>(StringComparer.Ordinal);
            foreach (var pair in binding.ValuesByVar)
            {
                if (string.IsNullOrWhiteSpace(pair.Key))
                {
                    continue;
                }

                var key = pair.Key.StartsWith("?", StringComparison.Ordinal)
                    ? pair.Key[1..]
                    : pair.Key;
                if (!output.ContainsKey(key))
                {
                    output[key] = pair.Value;
                }
            }

            yield return output;
        }
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent
{
}
#endif
