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
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ValidationInputMissing("State"));
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
        // Pass null for lastAppliedStateId: the rising-edge guard already prevents
        // spurious re-fires. The StateId guard would block legitimate re-application
        // when the user changes sliders and wants to restore the saved state.
        var service = new DesignStateReinstatementService();
        var result = service.Validate(snapshot, resolvedTargets, lastAppliedStateId: null);

        // ── Write values (only if result.Applied == true) ───────────────────────
        if (result.Applied)
        {
            ScheduleWriteValues(snapshot, designStateComponent, resolvedTargets);
            _lastAppliedStateId = snapshot.StateId;
        }

        // ── Surface blocked parameters as error bubbles ─────────────────────────
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
        SetOutputs(da, result, FormatStatus(result));
        Message = FormatMessage(result);
    }

    // ── Snapshot unwrapping ─────────────────────────────────────────────────────

    private static DesignStateSnapshot? UnwrapSnapshot(object? input)
    {
        if (input is null) return null;

        // Direct type match (fastest path — same assembly)
        if (input is DesignStateSnapshot direct) return direct;
        if (input is global::DG.DesignStateSnapshot publicDirect) return publicDirect;

        // Unwrap GH container first
        var raw = UnwrapGhContainer(input);
        if (raw is null) return null;

        // Try direct cast on unwrapped value
        if (raw is DesignStateSnapshot rawDirect) return rawDirect;
        if (raw is global::DG.DesignStateSnapshot rawPublic) return rawPublic;

        // Assembly mismatch fallback: type name matches but cast fails
        // because GH loaded a different copy of DG.Core.dll.
        // Reconstruct via reflection.
        var typeName = raw.GetType().FullName;
        if (typeName is "DG.Core.Models.DesignStateSnapshot" or "DG.DesignStateSnapshot")
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

    private static DesignStateSnapshot? ReconstructSnapshot(object foreign)
    {
        try
        {
            var foreignType = foreign.GetType();
            var stateId = foreignType.GetProperty("StateId")?.GetValue(foreign) as string ?? string.Empty;
            var capturedAtRaw = foreignType.GetProperty("CapturedAtUtc")?.GetValue(foreign);
            var capturedAt = capturedAtRaw is DateTimeOffset dto ? dto : DateTimeOffset.MinValue;
            var parametersRaw = foreignType.GetProperty("Parameters")?.GetValue(foreign);

            var snapshot = new DesignStateSnapshot
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

    private DesignStateComponent? FindUpstreamDesignState()
    {
        var found = FindDesignStateFromInput(1);
        if (found is not null) return found;
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

    /// <summary>
    /// Resolve the type and domain of a source parameter.
    /// MUST match <see cref="DesignStateComponent"/> classification:
    ///   GH_NumberSlider → always Number (ScriptVariable returns double regardless of DecimalPlaces).
    ///   GH_BooleanToggle → Boolean.
    /// </summary>
    private static (DesignStateParameterType? Type, double? DomainMin, double? DomainMax) ResolveSourceInfo(IGH_Param source)
    {
        if (source.Attributes?.GetTopLevel?.DocObject is GH_NumberSlider slider)
        {
            var min = (double)slider.Slider.Minimum;
            var max = (double)slider.Slider.Maximum;
            // Always Number — DesignStateComponent captures slider output via
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
        DesignStateSnapshot snapshot,
        DesignStateComponent designState,
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
