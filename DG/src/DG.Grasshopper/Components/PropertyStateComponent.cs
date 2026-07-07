#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

/// <summary>
/// PROPERTY STATE component. Composes a Rule, DataProperty, and PropValue into a PropState
/// for downstream DESIGN STATE composition. Each PropState is rule-scoped (one Rule +
/// one DataProperty + one value per PropState).
///
/// Usage:
///   1. Drop PROPERTY STATE on the canvas.
///   2. Wire a Rule to the "Rule" input.
///   3. Wire a DataProperty IRI string to the "DataProperty" input.
///   4. Wire a scalar value (Number, Integer, or Boolean) to the "PropValue" input.
///   5. Wire the "PropState" output to DESIGN STATE composition's PropState input.
///
/// Output list length is driven by PropValue. Rule and DataProperty at each index
/// are used when available; mismatched list lengths are tolerated — gaps produce
/// PropStates with empty RuleIri or DataPropertyIri.
/// </summary>
public sealed class PropertyStateComponent : GH_Component
{
    public PropertyStateComponent()
        : base(
            "PROPERTY STATE",
            "PROPSTATE",
            "Compose a Rule, DataProperty, and PropValue into a PropState for downstream DESIGN STATE composition.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("C5D2E7F8-1A3B-4C6D-9E0F-8B7A2C4D6E1F");

    protected override Bitmap Icon => DgIcons.PropertyState24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "Rule",
            "Rule",
            "Rule to associate with this property value (IRI reference).",
            GH_ParamAccess.list);
        pManager[0].Optional = true;

        pManager.AddGenericParameter(
            "DataProperty",
            "DataProperty",
            "DataProperty IRI (e.g. dg:hasHeight).",
            GH_ParamAccess.list);
        pManager[1].Optional = true;

        pManager.AddGenericParameter(
            "PropValue",
            "PropValue",
            "Calculated property value (Number, Integer, or Boolean scalar).",
            GH_ParamAccess.list);
        pManager[2].Optional = true;

        pManager.AddGenericParameter(
            "ObjState",
            "ObjState",
            "Optional per-object link: DG.ObjState list from OBJECT STATE, paired positionally with PropValue. "
                + "When provided, each PropState is tied to its object (ObjectRef), so the value binds only to "
                + "that object instead of being broadcast to all objects.",
            GH_ParamAccess.list);
        pManager[3].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "PropState",
            "PropState",
            "DG.PropState — wire to DESIGN STATE PropState input to compose into a DesignState.",
            GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var rules = new List<object?>();
        var dataProperties = new List<object?>();
        var propValues = new List<object?>();
        var objStates = new List<object?>();

        da.GetDataList(0, rules);
        da.GetDataList(1, dataProperties);
        da.GetDataList(2, propValues);
        da.GetDataList(3, objStates);

        // Output list length is driven by PropValue.
        var count = propValues.Count;
        if (count == 0)
        {
            da.SetDataList(0, new List<DG.PropState>());
            Message = "0 props";
            return;
        }

        var results = new List<DG.PropState>();
        for (var i = 0; i < count; i++)
        {
            var ruleObj = i < rules.Count ? GhCastingHelpers.TryRule(rules[i]) : null;
            var ruleIri = i < rules.Count ? ResolveRuleIri(rules[i]) : string.Empty;
            var dataPropertyIri = i < dataProperties.Count
                ? ResolveDataPropertyIri(dataProperties[i], ruleObj)
                : string.Empty;
            var scalar = UnwrapScalar(propValues[i]);
            var propValue = scalar is not null ? BuildParameter($"prop_{i}", dataPropertyIri, scalar) : null;

            if (propValue is null)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    $"PROPERTY STATE: Could not resolve PropValue at index {i}. Expected a Number, Integer, or Boolean scalar.");
                continue;
            }

            // Per-object link (optional): pair ObjState[i] with PropValue[i] positionally.
            var objState = i < objStates.Count ? GhCastingHelpers.TryObjState(objStates[i]) : null;
            var objectRef = string.IsNullOrWhiteSpace(objState?.ObjectRef) ? null : objState!.ObjectRef;

            var stateId = DesignStateIdGenerator.ComputePropStateId(ruleIri, dataPropertyIri, propValue, objectRef);

            results.Add(new DG.PropState
            {
                StateId = stateId,
                RuleIri = ruleIri,
                DataPropertyIri = dataPropertyIri,
                ObjectRef = objectRef,
                PropValue = propValue,
            });
        }

        da.SetDataList(0, results);
        Message = $"{results.Count} prop(s)";
    }

    private static string ResolveRuleIri(object? input)
    {
        if (input is null)
            return string.Empty;

        var rule = GhCastingHelpers.TryRule(input);
        if (rule is not null)
            return rule.Id ?? string.Empty;

        if (input is string s)
            return s;

        return input.ToString() ?? string.Empty;
    }

    /// <summary>
    /// Resolves the DataProperty IRI for this PropState. When the DataProperty input is
    /// the property VARIABLE emitted by RULE DECONSTRUCT (e.g. ?h) and a Rule is present,
    /// the IRI is resolved from the rule's DataPropertyAtom so it matches what the binder
    /// expects. Otherwise the input's string form is used verbatim (raw IRI wiring).
    /// </summary>
    private static string ResolveDataPropertyIri(object? input, DG.Core.Models.Rule? rule)
    {
        if (input is null)
            return string.Empty;

        var variable = GhCastingHelpers.TryVariable(input);
        if (variable is not null && !string.IsNullOrWhiteSpace(variable.Name) && rule is not null)
        {
            var resolved = DesignStateBindingService.ResolveDataPropertyIri(rule, variable.Name);
            if (!string.IsNullOrWhiteSpace(resolved))
                return resolved;
        }

        if (input is string s)
            return s;

        return input.ToString() ?? string.Empty;
    }

    private static object? UnwrapScalar(object? raw)
    {
        if (raw is global::Grasshopper.Kernel.Types.IGH_Goo goo)
            raw = goo.ScriptVariable();

        return raw switch
        {
            bool or int or long or double or float => raw,
            _ => null,
        };
    }

    private static DesignStateParameter BuildParameter(string parameterId, string displayName, object scalar)
    {
        return scalar switch
        {
            bool b => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Boolean,
                BooleanValue = b,
            },
            int i => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Integer,
                IntegerValue = i,
            },
            long l => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Integer,
                IntegerValue = l,
            },
            double d => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Number,
                NumberValue = d,
            },
            float f => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Number,
                NumberValue = f,
            },
            _ => throw new InvalidOperationException($"Unsupported scalar type for PropValue: {scalar.GetType().Name}"),
        };
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class PropertyStateComponent
{
}
#endif
