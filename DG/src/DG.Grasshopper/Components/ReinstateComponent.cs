#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using System.Drawing;
using CoreDesignStateParameter = DG.Core.Models.DesignStateParameter;

namespace DG.Grasshopper.Components;

/// <summary>
/// REINSTATE component. Applies a saved DesignStateSnapshot back to the upstream
/// Grasshopper parameters that originally fed a DESIGN STATE component.
///
/// Usage:
///   1. Wire a DesignStateSnapshot (from VALIDATION RUNS "States" output) to "State".
///   2. Wire the DESIGN STATE component instance to "DesignState".
///   3. Connect a Button or Boolean Toggle to "Apply".
///   4. On rising-edge of Apply, the component validates all parameters and, if all pass,
///      writes values back to upstream sliders/toggles.
/// </summary>
public sealed class ReinstateComponent : GH_Component
{
    private bool _lastApplyInput;
    private string? _lastAppliedStateId;
    private ReinstatementResult? _latestResult;

    public ReinstateComponent()
        : base(
            "REINSTATE",
            "REINSTATE",
            "Apply a saved design state back to Grasshopper parameters. Requires a DESIGN STATE component reference for target resolution.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63");

    protected override Bitmap Icon => new Bitmap(24, 24);

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "State",
            "State",
            "DesignStateSnapshot to apply. Wire from VALIDATION RUNS 'States' output or directly from DESIGN STATE.",
            GH_ParamAccess.item);

        pManager.AddGenericParameter(
            "DesignState",
            "DesignState",
            "Reference to the DESIGN STATE component instance. Used to resolve write targets by walking its input ports' Sources.",
            GH_ParamAccess.item);

        pManager.AddBooleanParameter(
            "Apply",
            "Apply",
            "Rising-edge trigger. Component fires on false→true transition only. Use a Button or Boolean Toggle.",
            GH_ParamAccess.item,
            false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "Result",
            "Result",
            "Full ReinstatementResult object for downstream tooling.",
            GH_ParamAccess.item);

        pManager.AddTextParameter(
            "Report",
            "Report",
            "Per-parameter status lines. Format: '{ParameterId}: {Status} — {Detail}'.",
            GH_ParamAccess.list);

        pManager.AddTextParameter(
            "Status",
            "Status",
            "Summary message: 'Applied N parameters' / 'Aborted: M blocked' / 'Unchanged (same state)' / 'Idle'.",
            GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        // Read inputs
        object? stateInput = null;
        if (!da.GetData(0, ref stateInput))
        {
            SetOutputs(da, null, "No state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "State input is required.");
            return;
        }

        var snapshot = GhCastingHelpers.Unwrap<DesignStateSnapshot>(stateInput)
                       ?? GhCastingHelpers.Unwrap<global::DG.DesignStateSnapshot>(stateInput);
        if (snapshot is null)
        {
            SetOutputs(da, null, "Invalid state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast State input to DesignStateSnapshot.");
            return;
        }

        object? dsInput = null;
        if (!da.GetData(1, ref dsInput))
        {
            SetOutputs(da, null, "No DesignState input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "DesignState component reference is required.");
            return;
        }

        var designStateComponent = GhCastingHelpers.Unwrap<DesignStateComponent>(dsInput);
        if (designStateComponent is null)
        {
            SetOutputs(da, null, "Invalid DesignState input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast DesignState input to DesignStateComponent.");
            return;
        }

        bool applyInput = false;
        if (!da.GetData(2, ref applyInput))
        {
            applyInput = false;
        }

        // Rising-edge detection (D-08)
        var isRisingEdge = applyInput && !_lastApplyInput;
        _lastApplyInput = applyInput;

        if (!isRisingEdge)
        {
            SetOutputs(da, _latestResult, _latestResult is null ? "Idle" : FormatStatus(_latestResult));
            return;
        }

        // Resolve targets (D-01 through D-04)
        var resolvedTargets = ResolveTargets(designStateComponent);

        // Validate via Core service
        var service = new DesignStateReinstatementService();
        var result = service.Validate(snapshot, resolvedTargets, _lastAppliedStateId);

        // Write values (only if result.Applied == true)
        if (result.Applied)
        {
            WriteValues(snapshot, designStateComponent, resolvedTargets);
            _lastAppliedStateId = snapshot.StateId;
        }

        _latestResult = result;
        SetOutputs(da, result, FormatStatus(result));
        Message = FormatMessage(result);
    }

    private static List<ResolvedTarget> ResolveTargets(DesignStateComponent designState)
    {
        var targets = new List<ResolvedTarget>();

        for (var i = 0; i < designState.Params.Input.Count; i++)
        {
            var ghParam = designState.Params.Input[i];
            var parameterId = string.IsNullOrWhiteSpace(ghParam.NickName)
                ? $"param_{i}"
                : ghParam.NickName.Trim();

            if (ghParam.Sources.Count == 0)
            {
                targets.Add(new ResolvedTarget(parameterId, TargetResolutionStatus.Missing, null, null, null));
                continue;
            }

            if (ghParam.Sources.Count > 1)
            {
                targets.Add(new ResolvedTarget(parameterId, TargetResolutionStatus.Ambiguous, null, null, null));
                continue;
            }

            // Single source — resolve type and domain
            var source = ghParam.Sources[0];
            var (targetType, domainMin, domainMax) = ResolveSourceInfo(source);

            targets.Add(new ResolvedTarget(parameterId, TargetResolutionStatus.Resolved, targetType, domainMin, domainMax));
        }

        return targets;
    }

    private static (DesignStateParameterType? Type, double? DomainMin, double? DomainMax) ResolveSourceInfo(IGH_Param source)
    {
        // Check if the source's owner is a GH_NumberSlider
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var min = (double)slider.Slider.Minimum;
            var max = (double)slider.Slider.Maximum;

            // GH_NumberSlider can be integer-mode or floating
            var type = slider.Slider.DecimalPlaces == 0
                ? DesignStateParameterType.Integer
                : DesignStateParameterType.Number;

            return (type, min, max);
        }

        // Check for boolean toggle
        if (source.Attributes?.GetTopLevel?.DocObject is GH_BooleanToggle)
        {
            return (DesignStateParameterType.Boolean, null, null);
        }

        // Fallback: try to determine type from parameter type
        if (source is Param_Number)
            return (DesignStateParameterType.Number, null, null);

        if (source is Param_Integer)
            return (DesignStateParameterType.Integer, null, null);

        if (source is Param_Boolean)
            return (DesignStateParameterType.Boolean, null, null);

        // Unknown source type — cannot determine
        return (null, null, null);
    }

    private static void WriteValues(
        DesignStateSnapshot snapshot,
        DesignStateComponent designState,
        List<ResolvedTarget> resolvedTargets)
    {
        for (var i = 0; i < designState.Params.Input.Count && i < resolvedTargets.Count; i++)
        {
            var target = resolvedTargets[i];
            if (target.Resolution != TargetResolutionStatus.Resolved)
                continue;

            var parameterId = target.ParameterId;
            var parameter = snapshot.Parameters.FirstOrDefault(
                p => string.Equals(p.ParameterId, parameterId, StringComparison.Ordinal));
            if (parameter is null)
                continue;

            var source = designState.Params.Input[i].Sources[0];
            WriteToSource(source, parameter);
        }

        // Trigger re-solve after all writes
        designState.OnPingDocument()?.NewSolution(false);
    }

    private static void WriteToSource(IGH_Param source, CoreDesignStateParameter parameter)
    {
        // Write to GH_NumberSlider
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var value = parameter.Type == DesignStateParameterType.Integer
                ? (decimal)(parameter.IntegerValue ?? 0)
                : (decimal)(parameter.NumberValue ?? 0.0);

            slider.SetSliderValue(value);
            return;
        }

        // Write to GH_BooleanToggle
        if (source.Attributes?.GetTopLevel?.DocObject is GH_BooleanToggle toggle)
        {
            toggle.Value = parameter.BooleanValue ?? false;
            toggle.ExpireSolution(false);
            return;
        }

        // Generic fallback: clear volatile data and add new value
        source.ClearData();
        switch (parameter.Type)
        {
            case DesignStateParameterType.Number:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new global::Grasshopper.Kernel.Types.GH_Number(parameter.NumberValue ?? 0.0));
                break;
            case DesignStateParameterType.Integer:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new global::Grasshopper.Kernel.Types.GH_Integer((int)(parameter.IntegerValue ?? 0)));
                break;
            case DesignStateParameterType.Boolean:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new global::Grasshopper.Kernel.Types.GH_Boolean(parameter.BooleanValue ?? false));
                break;
        }

        source.ExpireSolution(false);
    }

    private void SetOutputs(IGH_DataAccess da, ReinstatementResult? result, string status)
    {
        da.SetData(0, result);

        if (result is not null)
        {
            var reportLines = result.Reports
                .Select(r => $"{r.ParameterId}: {r.Status}" + (r.Detail is not null ? $" — {r.Detail}" : ""))
                .ToList();
            da.SetDataList(1, reportLines);
        }
        else
        {
            da.SetDataList(1, new List<string>());
        }

        da.SetData(2, status);
    }

    private static string FormatStatus(ReinstatementResult result)
    {
        if (result.Applied)
            return $"Applied {result.AppliedCount} parameters";
        if (result.Aborted)
            return $"Aborted: {result.BlockedCount} blocked";
        if (result.UnchangedCount > 0)
            return "Unchanged (same state)";
        return "Idle";
    }

    private static string FormatMessage(ReinstatementResult result)
    {
        if (result.Applied)
            return $"Applied {result.AppliedCount}";
        if (result.Aborted)
            return "Aborted";
        if (result.UnchangedCount > 0)
            return "Unchanged";
        return "Idle";
    }
}
#endif
