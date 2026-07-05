#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;
using System.Security.Cryptography;
using System.Text;

namespace DG.Grasshopper.Components;

/// <summary>
/// OBJECT STATE component. Composes Object, Geometry, and Label into an ObjState
/// for downstream DESIGN STATE composition.
///
/// Usage:
///   1. Drop OBJECT STATE on the canvas.
///   2. Wire Object references to the "Object" input (ElementRef, GUID, or string).
///   3. Wire Rhino geometry to the "Geometry" input (optional, in-process only, not serialized).
///   4. Wire labels to the "Label" input (optional display string).
///   5. Wire the "ObjState" output to DESIGN STATE composition's ObjState input.
///
/// Index-mismatch guard: All three inputs must have equal list lengths.
/// </summary>
public sealed class ObjectStateComponent : GH_Component
{
    public ObjectStateComponent()
        : base(
            "OBJECT STATE",
            "OBJSTATE",
            "Compose Object, Geometry, and Label into an ObjState for downstream DESIGN STATE composition.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("F9A1D8B2-C4E6-4F7A-9B5D-3E8C2A1F6D0B");

    protected override Bitmap Icon => DgIcons.ObjectState24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "Object",
            "Object",
            "Object reference (ElementRef, GUID, or string identifier).",
            GH_ParamAccess.list);
        pManager[0].Optional = true;

        pManager.AddGenericParameter(
            "Geometry",
            "Geometry",
            "Rhino geometry reference (optional, in-process handle, not serialized).",
            GH_ParamAccess.list);
        pManager[1].Optional = true;

        pManager.AddGenericParameter(
            "Label",
            "Label",
            "User-supplied display label (optional).",
            GH_ParamAccess.list);
        pManager[2].Optional = true;

        pManager.AddTextParameter(
            "Class",
            "Class",
            "Class IRI from METAGRAPH Objects output (e.g. ex:Building). Used for Class IRI matching in VALIDATOR.",
            GH_ParamAccess.list);
        pManager[3].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "ObjState",
            "ObjState",
            "DG.ObjState — wire to DESIGN STATE ObjState input to compose into a DesignState.",
            GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var objects = new List<object?>();
        var geometries = new List<object?>();
        var labels = new List<object?>();
        var classes = new List<string>();

        da.GetDataList(0, objects);
        da.GetDataList(1, geometries);
        da.GetDataList(2, labels);
        da.GetDataList(3, classes);

        // Index-mismatch guard (D-03): validate BEFORE iteration
        var count = objects.Count;
        if (count != geometries.Count || count != labels.Count || count != classes.Count)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.ObjStateMismatchedListLengths(count, geometries.Count, labels.Count, classes.Count));
            da.SetData(0, null);
            return;
        }

        var results = new List<DG.ObjState>();
        for (var i = 0; i < count; i++)
        {
            var objectRef = ResolveObjectRef(objects[i]);
            var geometry = geometries[i];
            var label = labels[i]?.ToString();
            var classIri = string.IsNullOrEmpty(classes[i]) ? null : classes[i];

            var stateId = ComputeObjStateId(objectRef, label);

            results.Add(new DG.ObjState
            {
                StateId = stateId,
                ObjectRef = objectRef,
                Geometry = geometry,
                Label = label,
                ClassIri = classIri,
                CapturedAtUtc = DateTimeOffset.UtcNow,
            });
        }

        da.SetDataList(0, results);
        Message = $"{results.Count} obj(s)";
    }

    private static string ResolveObjectRef(object? input)
    {
        if (input is null)
            return string.Empty;

        // Try ElementRef unwrapping via GhCastingHelpers
        var elementRef = GhCastingHelpers.TryElementRef(input);
        if (elementRef is not null)
            return elementRef.DgEntityId ?? string.Empty;

        // Fallback: string or ToString
        if (input is string s)
            return s;

        return input.ToString() ?? string.Empty;
    }

    private static string ComputeObjStateId(string objectRef, string? label)
    {
        var input = $"{objectRef}|{label ?? ""}";
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        var hex = Convert.ToHexString(hash)[..16];
        return $"OS_{hex}";
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ObjectStateComponent
{
}
#endif
