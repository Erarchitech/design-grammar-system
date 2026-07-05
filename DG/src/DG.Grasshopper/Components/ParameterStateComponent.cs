#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using System.Drawing;

namespace DG.Grasshopper.Components;

/// <summary>
/// PARAMETER STATE component. Collects named Number/Integer/Boolean inputs and assembles
/// them into a ParamState for attachment and filtering in Validation Runs or filtering in
/// Validation Runs.
///
/// Usage:
///   1. Drop PARAMETER STATE on the canvas.
///   2. Right-click the component → "Add input" to add a socket per parameter.
///   3. Rename each input's NickName to match the slider (e.g. "Height", "Floors", "Active").
///      The NickName becomes the stable ParameterId used for reinstatement matching.
///   4. Wire Number Sliders → Number inputs, Integer Sliders → Integer inputs,
///      Boolean Toggles → Boolean inputs.
///   5. Wire the "State" output to Validation Runs.State (or DESIGN STATE for v7.0+ composition).
/// </summary>
public sealed class ParameterStateComponent : GH_Component, IGH_VariableParameterComponent
{
    public ParameterStateComponent()
        : base(
            "PARAMETER STATE",
            "PARAMSTATE",
            "Capture named Number, Integer, and Boolean parameters into a reusable ParamState.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("A2E8C4F1-6B3D-4A9C-8E5F-2D7B0C1A3F6E");

    protected override Bitmap Icon => DgIcons.ParameterState24;

    // ── Inputs start with one placeholder. User adds more via right-click → "Add input".
    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "Value",
            "Value",
            "Number, Integer, or Boolean parameter. Rename this NickName to set the ParameterId (used for reinstatement matching).",
            GH_ParamAccess.item);
        pManager[0].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "State",
            "State",
            "DG.ParamState — wire to DESIGN STATE ParamState input to compose into a DesignState, or to downstream state consumers.",
            GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var parameters = new List<DesignStateParameter>();

        for (var i = 0; i < Params.Input.Count; i++)
        {
            var ghParam = Params.Input[i];

            // Derive stable ParameterId from the user-assigned NickName.
            var parameterId = string.IsNullOrWhiteSpace(ghParam.NickName)
                ? $"param_{i}"
                : ghParam.NickName.Trim();

            var displayName = string.IsNullOrWhiteSpace(ghParam.Name)
                ? parameterId
                : ghParam.Name.Trim();

            object? raw = null;
            if (!da.GetData(i, ref raw) || raw is null)
            {
                // Optional — skip inputs that are not connected or are null.
                continue;
            }

            // Unwrap GH_ObjectWrapper or IGH_Goo → native .NET scalar.
            var scalar = UnwrapScalar(raw);
            if (scalar is null)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    ErrorMessageTemplates.DesignStateTypeUnsupported(parameterId, raw.GetType().Name));
                continue;
            }

            var dgParam = BuildParameter(parameterId, displayName, scalar);
            if (dgParam is null)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    ErrorMessageTemplates.DesignStateTypeUnsupported(parameterId, scalar.GetType().Name));
                continue;
            }

            parameters.Add(dgParam);
        }

        if (parameters.Count == 0)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                "No parameters captured. Connect at least one Number Slider, Integer Slider, or Boolean Toggle and ensure its input is not null.");
            da.SetData(0, null);
            Message = "No params";
            return;
        }

        // Build snapshot. StateId is a deterministic content hash so identical slider
        // positions produce the same StateId — enabling reliable state-based filtering.
        var snapshot = BuildSnapshot(parameters);
        da.SetData(0, snapshot);
        Message = $"{parameters.Count} param(s)";
    }

    // ── IGH_VariableParameterComponent ──────────────────────────────────────────────

    /// <summary>Only allow adding/removing inputs, not outputs.</summary>
    public bool CanInsertParameter(GH_ParameterSide side, int index) =>
        side == GH_ParameterSide.Input;

    /// <summary>Keep at least one input so the component is never fully empty.</summary>
    public bool CanRemoveParameter(GH_ParameterSide side, int index) =>
        side == GH_ParameterSide.Input && Params.Input.Count > 1;

    /// <summary>
    /// Create a generic optional input when the user right-clicks → "Add input".
    /// The default NickName is "Value{N}" — user should rename it to the parameter's
    /// semantic name (e.g. "Height", "Floors") for stable reinstatement matching.
    /// </summary>
    public IGH_Param CreateParameter(GH_ParameterSide side, int index)
    {
        var n = Params.Input.Count + 1;
        return new Param_GenericObject
        {
            Name = $"Value {n}",
            NickName = $"Value{n}",
            Description = "Number, Integer, or Boolean parameter. Rename this NickName to set the ParameterId.",
            Access = GH_ParamAccess.item,
            Optional = true,
        };
    }

    public bool DestroyParameter(GH_ParameterSide side, int index) => true;

    /// <summary>Called after parameters are added/removed. No maintenance needed.</summary>
    public void VariableParameterMaintenance() { }

    // ── Helpers ─────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Unwrap an IGH_Goo or GH_ObjectWrapper to a native .NET scalar.
    /// Returns null for unsupported types.
    /// </summary>
    private static object? UnwrapScalar(object? raw)
    {
        // GH wraps values in typed goo (GH_Number, GH_Integer, GH_Boolean).
        // ScriptVariable() converts to native .NET type.
        if (raw is global::Grasshopper.Kernel.Types.IGH_Goo goo)
            raw = goo.ScriptVariable();

        return raw switch
        {
            bool or int or long or double or float => raw,
            _ => null,
        };
    }

    /// <summary>
    /// Map a native .NET scalar to a typed DesignStateParameter.
    /// GH Integer Slider → int, Number Slider → double, Boolean Toggle → bool.
    /// </summary>
    private static DesignStateParameter? BuildParameter(string parameterId, string displayName, object scalar)
    {
        return scalar switch
        {
            // Boolean Toggle
            bool b => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Boolean,
                BooleanValue = b,
            },

            // Integer Slider (GH outputs int)
            int i => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Integer,
                IntegerValue = i,
            },

            // Long (defensive — GH typically gives int, not long)
            long l => new DesignStateParameter
            {
                ParameterId = parameterId,
                DisplayName = displayName,
                Type = DesignStateParameterType.Integer,
                IntegerValue = l,
            },

            // Number Slider (GH outputs double)
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

            _ => null,
        };
    }

    private static ParamState BuildSnapshot(List<DesignStateParameter> parameters)
    {
        var snapshot = new ParamState
        {
            StateId = DesignStateIdGenerator.ComputeParamStateId(parameters),
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        foreach (var p in parameters)
            snapshot.Parameters.Add(p);

        return snapshot;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ParameterStateComponent
{
}
#endif
