#if GRASSHOPPER_SDK
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

/// <summary>
/// RULE BY ID (Phase 1303, 1303-CONTEXT D-38): picks one rule from METAGRAPH Rules by its
/// Rule_Id. Placed by CONNECTOR's automatic mapping instead of List Item(index), so adding or
/// reordering rules in the graph cannot shift which rule a PROPERTY STATE or VALIDATOR uses.
/// </summary>
public sealed class RuleByIdComponent : GH_Component
{
    public RuleByIdComponent()
        : base("RULE BY ID", "RULE BY ID", "Pick a DG rule from METAGRAPH Rules by its Rule_Id (no list index).", DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    // Fresh GUID for Phase 1303 plan 09.
    public override Guid ComponentGuid => new("6C1F3B8E-2A47-4D95-B0E6-91D7C4A35F28");

    protected override Bitmap Icon => DgIcons.RuleDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Rules", "Rules", "DG.Rule list from METAGRAPH", GH_ParamAccess.list);
        pManager.AddTextParameter("RuleId", "RuleId", "Rule_Id of the rule to pick, e.g. R_FAC_ASPECT_MIN_13_V", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Rule", "Rule", "The rule with this Rule_Id", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var rules = new List<object?>();
        var ruleId = string.Empty;
        da.GetDataList(0, rules);
        if (!da.GetData(1, ref ruleId) || string.IsNullOrWhiteSpace(ruleId))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Set RuleId.");
            return;
        }

        ruleId = ruleId.Trim();
        foreach (var item in rules)
        {
            var rule = GhCastingHelpers.TryRule(item);
            if (rule is not null && (string.Equals(rule.Id, ruleId, StringComparison.Ordinal) || string.Equals(rule.Name, ruleId, StringComparison.Ordinal)))
            {
                da.SetData(0, item);
                Message = ruleId;
                return;
            }
        }

        Message = "not found";
        AddRuntimeMessage(
            GH_RuntimeMessageLevel.Warning,
            rules.Count == 0 ? "No rules yet: connect METAGRAPH Rules (it loads after CONNECTOR signs in)." : $"Rule {ruleId} is not among the {rules.Count} rules of METAGRAPH.");
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class RuleByIdComponent
{
}
#endif
