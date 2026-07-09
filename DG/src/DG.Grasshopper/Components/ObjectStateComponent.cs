#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
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
///   2. Wire the ontology class to the "Object" input (a single OntologyClass from
///      METAGRAPH Objects — its Class IRI is broadcast to every geometry instance).
///      Per-instance ElementRef/GUID/string inputs are also supported (one per geometry).
///   3. Wire Rhino geometry to the "Geometry" input (one item per instance).
///   4. Wire labels to the "Label" input (optional; empty, or one per geometry).
///   5. Wire the "ObjState" output to DESIGN STATE (ObjState input) and, for per-object
///      properties, to PROPERTY STATE (ObjState input).
///
/// Output list length is driven by Geometry. A single OntologyClass on "Object" is
/// broadcast as the shared ClassIri across all instances. Each ObjState gets a UNIQUE
/// ObjectRef, resolved as: explicit per-instance ref → geometry reference GUID → index.
/// </summary>
public sealed class ObjectStateComponent : GH_Component
{
    public ObjectStateComponent()
        : base(
            "OBJECT STATE",
            "OBJSTATE",
            "Compose Object, Geometry, and Label into an ObjState for downstream DESIGN STATE composition.",
            DgComponentCategory.Category,
            DgComponentCategory.StatesSubcategory)
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
        var geometryGoos = new List<IGH_Goo>();
        var labels = new List<object?>();

        da.GetDataList(0, objects);
        da.GetDataList(1, geometryGoos);
        da.GetDataList(2, labels);

        // Output list length is driven by Geometry. Labels, when supplied, must match
        // Geometry length; an empty Label input is allowed (labels default to null).
        var geoCount = geometryGoos.Count;
        var labelCount = labels.Count;
        if (labelCount != 0 && labelCount != geoCount)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Error,
                ErrorMessageTemplates.ObjStateMismatchedListLengths(geoCount, labelCount));
            da.SetData(0, null);
            return;
        }

        // A single Object that is an ontology class is broadcast as the shared ClassIri
        // across every geometry instance (one class → many instances). Per-instance
        // identity (ObjectRef) is derived from the geometry (reference GUID) or index,
        // never from the shared class.
        var broadcastClassIri = objects.Count == 1 ? ResolveClassIri(objects[0]) : null;

        var results = new List<DG.ObjState>();
        for (var i = 0; i < geoCount; i++)
        {
            var perItemObject = i < objects.Count ? objects[i] : null;
            var classIri = broadcastClassIri ?? (perItemObject is not null ? ResolveClassIri(perItemObject) : null);

            var geometry = geometryGoos[i]?.ScriptVariable();
            var label = i < labels.Count ? labels[i]?.ToString() : null;

            // ObjectRef priority: explicit per-instance ref → geometry reference GUID → index.
            var objectRef = ResolveInstanceRef(perItemObject)
                ?? GeometryReferenceId(geometryGoos[i])
                ?? $"obj_{i}";

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

    /// <summary>
    /// Returns a per-instance object reference from the input, or null when the input is
    /// an ontology CLASS (a class is not an instance identity) or carries no usable id.
    /// </summary>
    private static string? ResolveInstanceRef(object? input)
    {
        if (input is null)
            return null;

        // OntologyClass is a class, not a per-instance identity — no ObjectRef from it.
        if (GhCastingHelpers.Unwrap<DG.Core.Models.OntologyClass>(input) is not null)
            return null;

        var elementRef = GhCastingHelpers.TryElementRef(input);
        if (elementRef is not null && !string.IsNullOrWhiteSpace(elementRef.DgEntityId))
            return elementRef.DgEntityId;

        if (input is string s && !string.IsNullOrWhiteSpace(s))
            return s.Trim();

        return null;
    }

    /// <summary>
    /// Extracts a stable per-instance identity from a referenced Rhino object's GUID,
    /// or null for internalized/computed geometry that has no reference.
    /// </summary>
    private static string? GeometryReferenceId(IGH_Goo? goo)
    {
        if (goo is IGH_GeometricGoo geometric && geometric.ReferenceID != Guid.Empty)
            return geometric.ReferenceID.ToString();

        return null;
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
