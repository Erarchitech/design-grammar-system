#if GRASSHOPPER_SDK
using DG.Core.Models;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using System.Drawing;
using System.Security.Cryptography;
using System.Text;

namespace DG.Grasshopper.Components;

/// <summary>
/// DESIGN STATE component. Collects named Number/Integer/Boolean inputs and serializes
/// them into a DesignStateSnapshot for attachment to Classificator runs or filtering in
/// Validation Runs.
///
/// Usage:
///   1. Drop DESIGN STATE on the canvas.
///   2. Right-click the component → "Add input" to add a socket per parameter.
///   3. Rename each input's NickName to match the slider (e.g. "Height", "Floors", "Active").
///      The NickName becomes the stable ParameterId used for reinstatement matching.
///   4. Wire Number Sliders → Number inputs, Integer Sliders → Integer inputs,
///      Boolean Toggles → Boolean inputs.
///   5. Wire the "State" output to Classificator.State and/or Validation Runs.State.
/// </summary>
public sealed class DesignStateComponent : GH_Component, IGH_VariableParameterComponent
{
    public DesignStateComponent()
        : base(
            "DESIGN STATE",
            "DSGSTATE",
            "Capture named Number, Integer, and Boolean parameters into a reusable design state snapshot.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("B3D1E7F2-A945-4C8B-B6F0-1A0D3C4E9B72");

    protected override Bitmap Icon => new Bitmap(24, 24);

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
            "DG.DesignStateSnapshot — wire to Classificator.State to attach this state to a validation run, or to Validation Runs.State to filter runs by this state.",
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
                    $"Input '{parameterId}' has unsupported type '{raw.GetType().Name}'. Connect a Number Slider, Integer Slider, or Boolean Toggle.");
                continue;
            }

            var dgParam = BuildParameter(parameterId, displayName, scalar);
            if (dgParam is null)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    $"Input '{parameterId}': could not classify value '{scalar}' as Number, Integer, or Boolean.");
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

    private static DesignStateSnapshot BuildSnapshot(List<DesignStateParameter> parameters)
    {
        var snapshot = new DesignStateSnapshot
        {
            StateId = ComputeStateId(parameters),
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        foreach (var p in parameters)
            snapshot.Parameters.Add(p);

        return snapshot;
    }

    /// <summary>
    /// Produce a 16-character hex StateId that is a deterministic hash of the
    /// sorted parameter ID + value pairs.
    ///
    /// Identical slider positions → identical StateId → state filter in VALIDATION RUNS
    /// correctly matches across different sessions.
    /// </summary>
    private static string ComputeStateId(IEnumerable<DesignStateParameter> parameters)
    {
        var sb = new StringBuilder();

        foreach (var p in parameters.OrderBy(x => x.ParameterId, StringComparer.Ordinal))
        {
            sb.Append(p.ParameterId);
            sb.Append('=');
            sb.Append(p.Type switch
            {
                DesignStateParameterType.Boolean => p.BooleanValue?.ToString(System.Globalization.CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Integer => p.IntegerValue?.ToString(System.Globalization.CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Number  => p.NumberValue?.ToString("R", System.Globalization.CultureInfo.InvariantCulture) ?? "null",
                _ => "null",
            });
            sb.Append(';');
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()));
        return Convert.ToHexString(hash)[..16];
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class DesignStateComponent
{
}
#endif
