#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
using System.Drawing;
using CoreDesignStateParameter = DG.Core.Models.DesignStateParameter;

namespace DG.Grasshopper.Components;

/// <summary>
/// REINSTATE component. Applies a saved DesignStateSnapshot back to the upstream
/// Grasshopper parameters that originally fed a DESIGN STATE component.
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
            "DesignStateSnapshot to apply. Wire from VALIDATION RUNS 'States' output or directly from DESIGN STATE 'State' output.",
            GH_ParamAccess.item);

        pManager.AddGenericParameter(
            "DesignState",
            "DesignState",
            "Wire the DESIGN STATE component's 'State' output here. The component is found by walking the wire to resolve write targets.",
            GH_ParamAccess.item);
        Params.Input[1].Optional = true;

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
        // ── Read State input ────────────────────────────────────────────────────
        object? stateInput = null;
        if (!da.GetData(0, ref stateInput))
        {
            SetOutputs(da, null, "No state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "State input is required.");
            return;
        }

        var snapshot = UnwrapSnapshot(stateInput);
        if (snapshot is null)
        {
            SetOutputs(da, null, "Invalid state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                $"Could not cast State input to DesignStateSnapshot. {DiagnoseInputType(stateInput)}");
            return;
        }

        // ── Find DesignStateComponent by walking wire sources ────────────────────
        var designStateComponent = FindUpstreamDesignState();
        if (designStateComponent is null)
        {
            SetOutputs(da, null, "No DESIGN STATE found.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                "Could not find a DESIGN STATE component upstream of the 'DesignState' input. " +
                "Wire the 'State' output of a DESIGN STATE component to this input.");
            return;
        }

        // ── Read Apply trigger ──────────────────────────────────────────────────
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

        // ── Resolve targets (D-01 through D-04) ────────────────────────────────
        var resolvedTargets = ResolveTargets(designStateComponent);

        // ── Validate via Core service ───────────────────────────────────────────
        var service = new DesignStateReinstatementService();
        var result = service.Validate(snapshot, resolvedTargets, _lastAppliedStateId);

        // ── Write values (only if result.Applied == true) ───────────────────────
        if (result.Applied)
        {
            WriteValues(snapshot, designStateComponent, resolvedTargets);
            _lastAppliedStateId = snapshot.StateId;
        }

        _latestResult = result;
        SetOutputs(da, result, FormatStatus(result));
        Message = FormatMessage(result);
    }

    // ── Snapshot unwrapping ─────────────────────────────────────────────────────

    /// <summary>
    /// Robust unwrapping of DesignStateSnapshot from GH wire data.
    /// Handles: direct cast, GH_ObjectWrapper (including nested wrappers and ScriptVariable),
    /// and generic IGH_Goo via ScriptVariable().
    /// </summary>
    private static DesignStateSnapshot? UnwrapSnapshot(object? input)
    {
        if (input is null) return null;

        // Direct type match (fastest path)
        if (input is DesignStateSnapshot direct) return direct;
        if (input is global::DG.DesignStateSnapshot publicDirect) return publicDirect;

        // GH_ObjectWrapper — the standard wrapper for Generic params
        if (input is GH_ObjectWrapper wrapper)
        {
            var val = wrapper.Value;
            if (val is DesignStateSnapshot ws) return ws;
            if (val is global::DG.DesignStateSnapshot wps) return wps;

            // Nested wrapper (rare but possible)
            if (val is GH_ObjectWrapper nested)
                return UnwrapSnapshot(nested);

            // Value itself might be IGH_Goo
            if (val is IGH_Goo innerGoo)
            {
                var innerSv = innerGoo.ScriptVariable();
                if (innerSv is DesignStateSnapshot isv) return isv;
                if (innerSv is global::DG.DesignStateSnapshot ipsv) return ipsv;
            }

            // ScriptVariable() on the wrapper itself
            var sv = wrapper.ScriptVariable();
            if (sv is DesignStateSnapshot svs) return svs;
            if (sv is global::DG.DesignStateSnapshot psvs) return psvs;

            // Last resort: the Value might be the right type but loaded from a different
            // assembly instance. Check by type name as fallback.
            if (val is not null && val.GetType().FullName is "DG.Core.Models.DesignStateSnapshot" or "DG.DesignStateSnapshot")
            {
                // Use reflection-free cast through common base — DesignStateSnapshot is not sealed
                // so DG.DesignStateSnapshot inherits from it. Try dynamic.
                try { return (DesignStateSnapshot)(dynamic)val; } catch { /* fallback failed */ }
            }
        }

        // Any IGH_Goo — unwrap via ScriptVariable()
        if (input is IGH_Goo goo)
        {
            var scriptVar = goo.ScriptVariable();
            if (scriptVar is DesignStateSnapshot gsv) return gsv;
            if (scriptVar is global::DG.DesignStateSnapshot gpsv) return gpsv;

            // Recursive for nested goo
            if (scriptVar is GH_ObjectWrapper nestedWrapper)
                return UnwrapSnapshot(nestedWrapper);
        }

        return null;
    }

    /// <summary>Diagnostic: get the inner type for error messages.</summary>
    private static string DiagnoseInputType(object? input)
    {
        if (input is null) return "Input is null.";
        if (input is GH_ObjectWrapper w)
        {
            var val = w.Value;
            return $"GH_ObjectWrapper.Value type: {val?.GetType().FullName ?? "null"} " +
                   $"(assembly: {val?.GetType().Assembly.GetName().Name ?? "?"})";
        }
        if (input is IGH_Goo g)
        {
            var sv = g.ScriptVariable();
            return $"IGH_Goo ({g.GetType().FullName}), ScriptVariable type: {sv?.GetType().FullName ?? "null"}";
        }
        return $"Raw type: {input.GetType().FullName}";
    }

    // ── Component discovery via wire traversal ──────────────────────────────────

    /// <summary>
    /// Find the DesignStateComponent by walking upstream from Input[1] (DesignState).
    /// Falls back to Input[0] (State) if Input[1] is not connected.
    /// </summary>
    private DesignStateComponent? FindUpstreamDesignState()
    {
        // Primary: walk Input[1] sources
        var found = FindDesignStateFromInput(1);
        if (found is not null) return found;

        // Fallback: walk Input[0] sources (State input might come directly from DESIGN STATE)
        return FindDesignStateFromInput(0);
    }

    private DesignStateComponent? FindDesignStateFromInput(int inputIndex)
    {
        if (inputIndex >= Params.Input.Count) return null;
        var input = Params.Input[inputIndex];
        if (input.Sources.Count == 0) return null;

        foreach (var source in input.Sources)
        {
            var docObj = source.Attributes?.GetTopLevel?.DocObject;
            if (docObj is DesignStateComponent dsc)
                return dsc;
        }

        return null;
    }

    // ── Target resolution ───────────────────────────────────────────────────────

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

            var source = ghParam.Sources[0];
            var (targetType, domainMin, domainMax) = ResolveSourceInfo(source);

            targets.Add(new ResolvedTarget(parameterId, TargetResolutionStatus.Resolved, targetType, domainMin, domainMax));
        }

        return targets;
    }

    private static (DesignStateParameterType? Type, double? DomainMin, double? DomainMax) ResolveSourceInfo(IGH_Param source)
    {
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var min = (double)slider.Slider.Minimum;
            var max = (double)slider.Slider.Maximum;
            var type = slider.Slider.DecimalPlaces == 0
                ? DesignStateParameterType.Integer
                : DesignStateParameterType.Number;
            return (type, min, max);
        }

        if (source.Attributes?.GetTopLevel?.DocObject is GH_BooleanToggle)
            return (DesignStateParameterType.Boolean, null, null);

        if (source is Param_Number)
            return (DesignStateParameterType.Number, null, null);
        if (source is Param_Integer)
            return (DesignStateParameterType.Integer, null, null);
        if (source is Param_Boolean)
            return (DesignStateParameterType.Boolean, null, null);

        return (null, null, null);
    }

    // ── Value writing ───────────────────────────────────────────────────────────

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

        designState.OnPingDocument()?.NewSolution(false);
    }

    private static void WriteToSource(IGH_Param source, CoreDesignStateParameter parameter)
    {
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var value = parameter.Type == DesignStateParameterType.Integer
                ? (decimal)(parameter.IntegerValue ?? 0)
                : (decimal)(parameter.NumberValue ?? 0.0);
            slider.SetSliderValue(value);
            return;
        }

        if (source.Attributes?.GetTopLevel?.DocObject is GH_BooleanToggle toggle)
        {
            toggle.Value = parameter.BooleanValue ?? false;
            toggle.ExpireSolution(false);
            return;
        }

        source.ClearData();
        switch (parameter.Type)
        {
            case DesignStateParameterType.Number:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new GH_Number(parameter.NumberValue ?? 0.0));
                break;
            case DesignStateParameterType.Integer:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new GH_Integer((int)(parameter.IntegerValue ?? 0)));
                break;
            case DesignStateParameterType.Boolean:
                source.AddVolatileData(new global::Grasshopper.Kernel.Data.GH_Path(0), 0,
                    new GH_Boolean(parameter.BooleanValue ?? false));
                break;
        }
        source.ExpireSolution(false);
    }

    // ── Output helpers ──────────────────────────────────────────────────────────

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
        if (result.Applied) return $"Applied {result.AppliedCount} parameters";
        if (result.Aborted) return $"Aborted: {result.BlockedCount} blocked";
        if (result.UnchangedCount > 0) return "Unchanged (same state)";
        return "Idle";
    }

    private static string FormatMessage(ReinstatementResult result)
    {
        if (result.Applied) return $"Applied {result.AppliedCount}";
        if (result.Aborted) return "Aborted";
        if (result.UnchangedCount > 0) return "Unchanged";
        return "Idle";
    }
}
#endif
