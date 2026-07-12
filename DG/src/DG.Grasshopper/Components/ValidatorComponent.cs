#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using DG.Core.Validation;
using DG.Grasshopper.Validation;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent : GH_Component
{
    private readonly RuleEvaluator _ruleEvaluator = new();

    public ValidatorComponent()
        : base("VALIDATOR", "VALIDATOR", "Validate parametric state against DG rules.", DgComponentCategory.Category, DgComponentCategory.ActionsSubcategory)
    {
    }

    public override Guid ComponentGuid => new("C202D04A-9CC2-4CD1-9F47-C77D4093D447");

    protected override Bitmap Icon => DgIcons.Validator24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Rule", "Rule", "DG.Rule from RULE DECONSTRUCT or METAGRAPH", GH_ParamAccess.item);
        pManager.AddGenericParameter("DesignState", "DesignState", "Composed DG.DesignState from DESIGN STATE component", GH_ParamAccess.item);
        pManager[1].Optional = true;
        pManager.AddBooleanParameter("SendValid", "SendValid", "Set true to evaluate and publish results to data-service", GH_ParamAccess.item, false);
        pManager.AddTextParameter("DataServiceUrl", "DataServiceUrl", "DG data-service base URL", GH_ParamAccess.item, "http://localhost:8000");
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddBooleanParameter("ValidStatus", "ValidStatus", "Per-ObjState Boolean list: true=passing, false=failing. Index-matched to DesignState.ObjStates order.", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleName", "RuleName", "Rule name from the bound Rule", GH_ParamAccess.item);
        pManager.AddTextParameter("RuleDescription", "RuleDescription", "Rule description from the bound Rule", GH_ParamAccess.item);
        pManager.AddTextParameter("Report", "Report", "Per-rule report lines", GH_ParamAccess.list);
        pManager.AddTextParameter("FailingBindings", "FailingBindings", "Failing bindings in format: b(building32): h(83), w(54)", GH_ParamAccess.list);
        pManager.AddTextParameter("SendStatus", "SendStatus", "Speckle publish status (published / Not requested / error message)", GH_ParamAccess.item);
        pManager.AddTextParameter("ValidationRunId", "ValidationRunId", "Validation run identifier returned by DG backend", GH_ParamAccess.item);
        pManager.AddTextParameter("ModelViewerUrl", "ModelViewerUrl", "Model Viewer URL returned by DG backend", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        // 1. Read inputs
        object? ruleInput = null;
        if (!da.GetData(0, ref ruleInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Rule input is required.");
            return;
        }

        var rule = GhCastingHelpers.TryRule(ruleInput);
        if (rule is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Rule input.");
            return;
        }

        object? designStateInput = null;
        da.GetData(1, ref designStateInput);
        var designState = GhCastingHelpers.TryDesignState(designStateInput);

        var sendValid = false;
        da.GetData(2, ref sendValid);

        var dataServiceUrl = "http://localhost:8000";
        da.GetData(3, ref dataServiceUrl);

        // 2. If DesignState is null: warning, continue with empty
        if (designState is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "DesignState input is empty. Connect a DESIGN STATE component.");
        }

        // 3. Bind via DesignStateBindingService (D-03)
        var bindings = designState is not null && designState.ObjStates.Count > 0
            ? DesignStateBindingService.BuildBindings(rule, designState)
            : new List<BindingRow>();

        // 4. Evaluate via RuleEvaluator (single rule)
        var result = _ruleEvaluator.EvaluateRule(rule, bindings);

        // 5. Build ValidStatus per D-01/D-02
        var validStatus = new List<bool>();
        if (designState is not null)
        {
            var failingBindingsSet = new HashSet<BindingRow>(result.FailingBindings);
            for (var i = 0; i < designState.ObjStates.Count; i++)
            {
                // D-01: every ObjState gets ValidStatus[i], index-matched
                // D-02: non-matching (bindingExists==false) get false but excluded from overall pass AND
                var bindingExists = i < bindings.Count;
                validStatus.Add(bindingExists && !failingBindingsSet.Contains(bindings[i]));
            }
        }

        // 6. Set outputs
        da.SetDataList(0, validStatus);
        da.SetData(1, rule.Name);
        da.SetData(2, rule.Description);
        var reportLines = new List<string> { ValidationReportFormatter.ToReportLine(result) };
        da.SetDataList(3, reportLines);
        var failingFormatted = result.FailingBindings
            .Select(b => FailingBindingFormatter.Format(rule, b))
            .ToList();
        da.SetDataList(4, failingFormatted);

        // 7. Publish on SendValid=true
        var sendStatus = "Not requested";
        var validationRunId = string.Empty;
        var modelViewerUrl = string.Empty;
        if (sendValid)
        {
            try
            {
                var response = ValidationPublishClient.Publish(
                    new[] { rule },
                    new[] { result },
                    bindings,
                    dataServiceUrl,
                    designState,
                    validStatus);
                sendStatus = string.IsNullOrWhiteSpace(response.Status) ? "published" : response.Status;
                validationRunId = response.RunId;
                modelViewerUrl = response.ModelViewerUrl;

                // 7a. Surface SHACL findings (D-15): Report lines + runtime messages, capped
                // at Warning -- a SHACL data-integrity finding must never render this
                // component as errored/failed. GH_RuntimeMessageLevel.Error stays reserved
                // for the publish-exception catch block below.
                var shacl = response.Shacl;
                if (shacl?.Results is { Count: > 0 })
                {
                    foreach (var finding in shacl.Results)
                    {
                        var severity = finding.Severity ?? string.Empty;
                        var line = ErrorMessageTemplates.ShaclViolation(severity, finding.What ?? string.Empty, finding.Where ?? string.Empty, finding.HowToFix ?? string.Empty);
                        reportLines.Add(line);

                        var level = severity.Trim().ToLowerInvariant() switch
                        {
                            "violation" => GH_RuntimeMessageLevel.Warning,
                            "warning" => GH_RuntimeMessageLevel.Warning,
                            "info" => GH_RuntimeMessageLevel.Remark,
                            _ => GH_RuntimeMessageLevel.Remark,
                        };
                        AddRuntimeMessage(level, line);
                    }
                    da.SetDataList(3, reportLines);
                }
                else if (shacl is not null && (shacl.Status == "unavailable" || shacl.Status == "timeout"))
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, $"SHACL was not evaluated for this run ({shacl.Status}).");
                }
            }
            catch (Exception ex)
            {
                sendStatus = $"Publish failed: {ex.Message}";
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, $"Publish failed: {ex.Message}");
            }
        }
        da.SetData(5, sendStatus);
        da.SetData(6, validationRunId);
        da.SetData(7, modelViewerUrl);
        Message = designState is not null
            ? $"{validStatus.Count(v => v)} / {validStatus.Count} pass | {sendStatus}"
            : "No DesignState";
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent
{
}
#endif
