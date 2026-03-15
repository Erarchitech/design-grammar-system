#if GRASSHOPPER_SDK
using DG.Core.Classification;
using DG.Core.Models;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;
using System.Drawing;
using CoreElementRef = DG.Core.Models.ElementRef;
using CoreVariable = DG.Core.Models.Variable;

namespace DG.Grasshopper.Components;

public sealed class ClassificatorComponent : GH_Component
{
    public ClassificatorComponent()
        : base("CLASSIFICATOR", "CLASSIFICATOR", "Map GH values to SWRL variables.", DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("154456A8-3F84-48E9-B60C-A66D84A6D4B1");

    protected override Bitmap Icon => DgIcons.Classificator24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Variables", "Variables", "DG.Variable list", GH_ParamAccess.list);
        pManager.AddGenericParameter("Values", "Values", "DataTree where branch index matches variable index", GH_ParamAccess.tree);
        pManager.AddGenericParameter("ElementRefs", "ElementRefs", "Optional DataTree where branch index matches variable index and each item carries a DG entity id plus optional geometry", GH_ParamAccess.tree);
        pManager[2].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("BoundVariables", "BoundVariables", "List of binding rows", GH_ParamAccess.list);
        pManager.AddTextParameter("MissingVariables", "MissingVariables", "Variables missing value branches", GH_ParamAccess.list);
        pManager.AddTextParameter("Status", "Status", "Classification status", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var variableInputs = new List<object>();
        if (!da.GetDataList(0, variableInputs))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Variables input is required.");
            return;
        }

        if (!da.GetDataTree(1, out GH_Structure<IGH_Goo>? valueTree))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Values tree input is required.");
            return;
        }

        GH_Structure<IGH_Goo>? elementRefTree = null;
        var hasElementRefTree = da.GetDataTree(2, out elementRefTree) && elementRefTree is not null;

        var variables = variableInputs
            .Select(GhCastingHelpers.TryVariable)
            .Where(variable => variable is not null)
            .Select(variable => variable!)
            .ToList();

        var valuesByVariable = new Dictionary<string, IReadOnlyList<object?>>(StringComparer.Ordinal);
        var elementRefsByVariable = new Dictionary<string, IReadOnlyList<CoreElementRef?>>(StringComparer.Ordinal);
        for (var index = 0; index < variables.Count; index++)
        {
            CoreVariable variable = variables[index];
            var branchValues = index < valueTree.Branches.Count
                ? valueTree.Branches[index].Select(GhCastingHelpers.ToRawValue).ToList()
                : new List<object?>();
            var branchElementRefs = new List<CoreElementRef?>();
            if (hasElementRefTree && index < elementRefTree!.Branches.Count)
            {
                var branch = elementRefTree.Branches[index];
                for (var rowIndex = 0; rowIndex < branch.Count; rowIndex++)
                {
                    var fallbackEntityValue = rowIndex < branchValues.Count ? branchValues[rowIndex] : null;
                    branchElementRefs.Add(GhCastingHelpers.ToElementRef(branch[rowIndex], fallbackEntityValue));
                }
            }

            valuesByVariable[variable.Name] = branchValues;
            elementRefsByVariable[variable.Name] = branchElementRefs;
        }

        var classification = VariableBinder.BuildBindings(
            variables,
            valuesByVariable,
            hasElementRefTree ? elementRefsByVariable : null);
        da.SetDataList(0, classification.BoundVariables);
        da.SetDataList(1, classification.MissingVariables);
        da.SetData(2, classification.Status);
        Message = classification.Status;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ClassificatorComponent
{
}
#endif
