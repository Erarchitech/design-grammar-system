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
///   2. Wire Object references to the "Object" input (ElementRef, GUID, string,
///      or OntologyClass from METAGRAPH Objects output — Class IRI is extracted
///      from the Object input when it carries OntologyClass information).
///   3. Wire Rhino geometry to the "Geometry" input (optional, in-process only, not serialized).
///   4. Wire labels to the "Label" input (optional display string).
///   5. Wire the "ObjState" output to DESIGN STATE composition's ObjState input.
///
/// Output list length is driven by Geometry and Label (they must be equal).
/// Object is an independent input — gaps are filled with empty ObjectRef.
/// Class IRI is resolved from the Object input (OntologyClass IRI, or null).
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
            "Object reference (ElementRef, GUID, string, or OntologyClass from METAGRAPH Objects — class IRI is extracted from OntologyClass).",
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

        da.GetDataList(0, objects);
        da.GetDataList(1, geometries);
        da.GetDataList(2, labels);

        // Output list length is driven by Geometry and Label — they must be equal.
        // Object is an independent input (may differ in length).
        var geoCount = geometries.Count;
        var labelCount = labels.Count;
        if (geoCount != labelCount)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.ObjStateMismatchedListLengths(geoCount, labelCount));
            da.SetData(0, null);
            return;
        }

        var results = new List<DG.ObjState>();
        for (var i = 0; i < geoCount; i++)
        {
            var objectRef = i < objects.Count ? ResolveObjectRef(objects[i]) : string.Empty;
            var classIri = i < objects.Count ? ResolveClassIri(objects[i]) : null;
            var geometry = geometries[i];
            var label = labels[i]?.ToString();

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

        // OntologyClass carries IRI + Label but no DgEntityId —
        // use Label as the object reference display, IRI as identity fallback.
        var ontClass = GhCastingHelpers.Unwrap<DG.Core.Models.OntologyClass>(input);
        if (ontClass is not null)
            return string.IsNullOrWhiteSpace(ontClass.Label) ? ontClass.Iri : ontClass.Label;

        // Try ElementRef unwrapping via GhCastingHelpers
        var elementRef = GhCastingHelpers.TryElementRef(input);
        if (elementRef is not null)
            return elementRef.DgEntityId ?? string.Empty;

        // Fallback: string or ToString
        if (input is string s)
            return s;

        return input.ToString() ?? string.Empty;
    }

    /// <summary>
    /// Extract Class IRI from the Object input when it carries OntologyClass information.
    /// Returns null for non-OntologyClass inputs (ElementRef, GUID, string, etc.).
    /// </summary>
    private static string? ResolveClassIri(object? input)
    {
        if (input is null)
            return null;

        var ontClass = GhCastingHelpers.Unwrap<DG.Core.Models.OntologyClass>(input);
        if (ontClass is not null && !string.IsNullOrWhiteSpace(ontClass.Iri))
            return ontClass.Iri;

        return null;
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
