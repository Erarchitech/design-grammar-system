#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
using System.Collections;
using System.Drawing;
using System.Reflection;
using CoreDesignStateParameter = DG.Core.Models.DesignStateParameter;

namespace DG.Grasshopper.Components;

/// <summary>
/// PARAMETER REINSTATE component. Applies a saved ParamState back to the upstream
/// Grasshopper sliders/toggles that originally fed a PARAMETER STATE component.
/// Required Target input wired from PARAMETER STATE. Rising-edge Reinstate trigger.
/// </summary>
public sealed class ParameterReinstateComponent : GH_Component
{
    private bool _lastApplyInput = true; // true prevents first-solve auto-fire
    private ReinstatementResult? _latestResult;
    private ParamState? _latestParamState;

    public ParameterReinstateComponent()
        : base(
            "PARAMETER REINSTATE",
            "PARAMREIN",
            "Apply a saved ParamState back to Grasshopper sliders/toggles. Required Target input wired from PARAMETER STATE. Rising-edge Reinstate trigger.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("8F9D0A1B-2C3D-4E4F-5A5B-6C7D8E9F0A1B");

    protected override Bitmap Icon => DgIcons.ParameterReinstate24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "ParamState",
            "ParamState",
            "ParamState to apply. Wire from DESIGN STATE DECONSTRUCT or PARAMETER STATE State output.",
            GH_ParamAccess.item);

        pManager.AddGenericParameter(
            "Target",
            "Target",
            "Required: Wire the State output of a PARAMETER STATE component. REINSTATE walks this wire to discover sliders/toggles.",
            GH_ParamAccess.item);

        pManager.AddBooleanParameter(
            "Reinstate",
            "Reinstate",
            "Rising-edge trigger -- fires on false->true transition. Use a Button or Boolean Toggle.",
            GH_ParamAccess.item,
            false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "Parameters",
            "Parameters",
            "All captured DesignStateParameters from the input ParamState (D-05). Cross-reference with StateStatus to filter applied vs. blocked.",
            GH_ParamAccess.list);

        pManager.AddGenericParameter(
            "StateStatus",
            "StateStatus",
            "Per-parameter ReinstatementStatus list, index-matched to Parameters (D-04). Same length, same order as Parameters.",
            GH_ParamAccess.list);

        pManager.AddTextParameter(
            "Status",
            "Status",
            "Summary: Applied N parameters / Aborted: M blocked / Unchanged (same state) / Idle (D-06).",
            GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        // ── Read ParamState input ───────────────────────────────────────────────
        object? stateInput = null;
        if (!da.GetData(0, ref stateInput))
        {
            _latestParamState = null;
            SetOutputs(da, null, "No state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ValidationInputMissing("ParamState"));
            return;
        }

        var snapshot = UnwrapSnapshot(stateInput);
        if (snapshot is null)
        {
            _latestParamState = null;
            SetOutputs(da, null, "Invalid state input.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                $"Could not cast ParamState input to ParamState. {DiagnoseInputType(stateInput)}");
            return;
        }

        _latestParamState = snapshot;

        // ── Find ParameterStateComponent by walking wire sources ────────────────
        // D-02: searches Input 1 (Target) ONLY — no fallback to Input 0
        var designStateComponent = FindUpstreamDesignState();
        if (designStateComponent is null)
        {
            SetOutputs(da, null, "No PARAMETER STATE found.");
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.ReinstateSourceNotFound());
            return;
        }

        // ── Read Reinstate trigger ──────────────────────────────────────────────
        bool applyInput = false;
        if (!da.GetData(2, ref applyInput))
        {
            applyInput = false;
        }

        // Rising-edge detection (D-08): _lastApplyInput starts true so first
        // solve with Reinstate=true does NOT auto-fire.
        var isRisingEdge = applyInput && !_lastApplyInput;
        _lastApplyInput = applyInput;

        if (!isRisingEdge)
        {
            SetOutputs(da, _latestResult, _latestResult is null ? "Idle" : ErrorMessageTemplates.FormatStatus(_latestResult));
            return;
        }

        // ── Resolve targets ─────────────────────────────────────────────────────
        var resolvedTargets = ResolveTargets(designStateComponent);

        // ── Validate via Core service ───────────────────────────────────────────
        var service = new DesignStateReinstatementService();
        var result = service.Validate(snapshot, resolvedTargets, lastAppliedStateId: null);

        // ── Write values (only if result.Applied == true) ───────────────────────
        if (result.Applied)
        {
            ScheduleWriteValues(snapshot, designStateComponent, resolvedTargets);
        }

        // ── Surface blocked parameters as warning bubbles ───────────────────────
        if (result.Aborted)
        {
            foreach (var report in result.Reports)
            {
                if (report.Status is ReinstatementStatus.MissingTarget
                    or ReinstatementStatus.TypeMismatch
                    or ReinstatementStatus.AmbiguousTarget
                    or ReinstatementStatus.OutOfRange)
                {
                    AddRuntimeMessage(
                        GH_RuntimeMessageLevel.Warning,
                        ErrorMessageTemplates.ReinstatementBlocked(
                            report.ParameterId, report.Status, report.Detail ?? ""));
                }
            }
        }

        _latestResult = result;
        SetOutputs(da, result, ErrorMessageTemplates.FormatStatus(result));
        Message = ErrorMessageTemplates.FormatMessage(result);
    }

    // ── Snapshot unwrapping ─────────────────────────────────────────────────────

    private static ParamState? UnwrapSnapshot(object? input)
    {
        if (input is null) return null;

        // Direct type match (fastest path -- same assembly)
        if (input is ParamState direct) return direct;
        if (input is global::DG.ParamState publicDirect) return publicDirect;

        // Unwrap GH container first
        var raw = UnwrapGhContainer(input);
        if (raw is null) return null;

        // Try direct cast on unwrapped value
        if (raw is ParamState rawDirect) return rawDirect;
        if (raw is global::DG.ParamState rawPublic) return rawPublic;

        // Assembly mismatch fallback: type name matches but cast fails
        // because GH loaded a different copy of DG.Core.dll.
        // Reconstruct via reflection.
        var typeName = raw.GetType().FullName;
        if (typeName is "DG.Core.Models.ParamState" or "DG.ParamState")
        {
            return ReconstructSnapshot(raw);
        }

        return null;
    }

    private static object? UnwrapGhContainer(object? input)
    {
        if (input is null) return null;

        if (input is not IGH_Goo and not GH_ObjectWrapper)
            return input;

        if (input is GH_ObjectWrapper wrapper)
        {
            var val = wrapper.Value;
            if (val is GH_ObjectWrapper nested)
                return UnwrapGhContainer(nested);
            if (val is IGH_Goo innerGoo)
                return innerGoo.ScriptVariable();
            return val;
        }

        if (input is IGH_Goo goo)
        {
            var sv = goo.ScriptVariable();
            if (sv is GH_ObjectWrapper svWrapper)
                return UnwrapGhContainer(svWrapper);
            return sv;
        }

        return input;
    }

    private static ParamState? ReconstructSnapshot(object foreign)
    {
        try
        {
            var foreignType = foreign.GetType();
            var stateId = foreignType.GetProperty("StateId")?.GetValue(foreign) as string ?? string.Empty;
            var capturedAtRaw = foreignType.GetProperty("CapturedAtUtc")?.GetValue(foreign);
            var capturedAt = capturedAtRaw is DateTimeOffset dto ? dto : DateTimeOffset.MinValue;
            var parametersRaw = foreignType.GetProperty("Parameters")?.GetValue(foreign);

            var snapshot = new ParamState
            {
                StateId = stateId,
                CapturedAtUtc = capturedAt,
            };

            if (parametersRaw is IEnumerable paramCollection)
            {
                foreach (var foreignParam in paramCollection)
                {
                    if (foreignParam is null) continue;
                    var param = ReconstructParameter(foreignParam);
                    if (param is not null)
                        snapshot.Parameters.Add(param);
                }
            }

            return snapshot;
        }
        catch
        {
            return null;
        }
    }

    private static CoreDesignStateParameter? ReconstructParameter(object foreign)
    {
        try
        {
            var t = foreign.GetType();
            var parameterId = t.GetProperty("ParameterId")?.GetValue(foreign) as string ?? string.Empty;
            var displayName = t.GetProperty("DisplayName")?.GetValue(foreign) as string ?? string.Empty;

            var typeRaw = t.GetProperty("Type")?.GetValue(foreign);
            var paramType = typeRaw is not null
                ? (DesignStateParameterType)(int)typeRaw
                : DesignStateParameterType.Number;

            var numberValue = t.GetProperty("NumberValue")?.GetValue(foreign) as double?;
            var integerValue = t.GetProperty("IntegerValue")?.GetValue(foreign) as long?;
            var booleanValue = t.GetProperty("BooleanValue")?.GetValue(foreign) as bool?;

            return new CoreDesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = paramType,
                NumberValue = numberValue,
                IntegerValue = integerValue,
                BooleanValue = booleanValue,
            };
        }
        catch
        {
            return null;
        }
    }

    private static string DiagnoseInputType(object? input)
    {
        if (input is null) return "Input is null.";
        var raw = UnwrapGhContainer(input);
        if (raw is not null && raw != input)
            return $"Unwrapped type: {raw.GetType().FullName} (assembly: {raw.GetType().Assembly.GetName().Name})";
        if (input is GH_ObjectWrapper w)
            return $"GH_ObjectWrapper.Value type: {w.Value?.GetType().FullName ?? "null"} (assembly: {w.Value?.GetType().Assembly.GetName().Name ?? "?"})";
        return $"Raw type: {input.GetType().FullName}";
    }

    // ── Component discovery via wire traversal ──────────────────────────────────

    private ParameterStateComponent? FindUpstreamDesignState()
    {
        // D-02: searches Input 1 (Target) ONLY — no fallback to Input 0
        return FindDesignStateFromInput(1);
    }

    private ParameterStateComponent? FindDesignStateFromInput(int inputIndex)
    {
        if (inputIndex >= Params.Input.Count) return null;
        var input = Params.Input[inputIndex];
        if (input.Sources.Count == 0) return null;

        foreach (var source in input.Sources)
        {
            var docObj = source.Attributes?.GetTopLevel?.DocObject;
            if (docObj is ParameterStateComponent dsc)
                return dsc;
        }

        return null;
    }

    // ── Target resolution ───────────────────────────────────────────────────────

    private static List<ResolvedTarget> ResolveTargets(ParameterStateComponent designState)
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

    /// <summary>
    /// Resolve the type and domain of a source parameter.
    /// MUST match <see cref="ParameterStateComponent"/> classification:
    ///   GH_NumberSlider → always Number (ScriptVariable returns double regardless of DecimalPlaces).
    ///   GH_BooleanToggle → Boolean.
    /// </summary>
    private static (DesignStateParameterType? Type, double? DomainMin, double? DomainMax) ResolveSourceInfo(IGH_Param source)
    {
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var min = (double)slider.Slider.Minimum;
            var max = (double)slider.Slider.Maximum;
            // Always Number — ParameterStateComponent captures slider output via
            // ScriptVariable() which returns double regardless of DecimalPlaces.
            return (DesignStateParameterType.Number, min, max);
        }

        if (source.Attributes?.GetTopLevel?.DocObject is GH_BooleanToggle)
            return (DesignStateParameterType.Boolean, null, null);

        if (source is Param_Number) return (DesignStateParameterType.Number, null, null);
        if (source is Param_Integer) return (DesignStateParameterType.Integer, null, null);
        if (source is Param_Boolean) return (DesignStateParameterType.Boolean, null, null);

        return (null, null, null);
    }

    // ── Value writing (deferred via ScheduleSolution) ───────────────────────────

    /// <summary>
    /// Schedule value writes AFTER the current solution completes.
    /// Writing sliders during an active SolveInstance can be silently dropped
    /// because the solution is already in progress. ScheduleSolution defers
    /// the write to a fresh solution pass.
    /// </summary>
    private static void ScheduleWriteValues(
        ParamState snapshot,
        ParameterStateComponent designState,
        List<ResolvedTarget> resolvedTargets)
    {
        var doc = designState.OnPingDocument();
        if (doc is null) return;

        // Capture the write data for the callback closure
        var writeActions = new List<Action>();

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

            var ghInput = designState.Params.Input[i];
            if (ghInput.Sources.Count == 0) continue;
            var source = ghInput.Sources[0];

            // Capture values for closure
            var paramCopy = parameter;
            var sourceCopy = source;
            writeActions.Add(() => WriteToSource(sourceCopy, paramCopy));
        }

        if (writeActions.Count == 0) return;

        doc.ScheduleSolution(5, _ =>
        {
            foreach (var write in writeActions)
                write();
        });
    }

    private static void WriteToSource(IGH_Param source, CoreDesignStateParameter parameter)
    {
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            // Snapshot always stores Number type for sliders (ScriptVariable → double).
            // Use NumberValue for the write regardless of the slider's DecimalPlaces mode.
            var value = (decimal)(parameter.NumberValue ?? 0.0);
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
        // D-05: Parameters output — ALL params from _latestParamState, not just applied
        da.SetDataList(0, _latestParamState is not null
            ? _latestParamState.Parameters.ToList()
            : new List<DesignStateParameter>());

        // D-04: StateStatus output — index-matched to Parameters, same length and order
        da.SetDataList(1, result?.Reports.Select(r => r.Status).ToList() ?? new List<ReinstatementStatus>());

        // D-06: Status output — summary text
        da.SetData(2, status);
    }
}
#endif
