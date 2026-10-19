#if GRASSHOPPER_SDK
using System.Text.Json;
using DG.Core.Mapping;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;

namespace DG.Grasshopper.Mapping;

/// <summary>A persisted, exact selection; no fallback to the complete source on invalid addresses.</summary>
public sealed class MappingSubsetComponent : GH_Component
{
    public MappingSubsetComponent() : base("MAPPING SELECTION", "MAP SELECT",
        "Only explicitly committed source branches/items. Changed sources require mapping again.", "DG", "Mapping") { }

    public override Guid ComponentGuid => new("608a0958-53f0-4918-b5d6-72f7c7d28b90");
    public override GH_Exposure Exposure => GH_Exposure.hidden;
    private string _selection = "[]";
    private bool _measure;
    private string _classIri = string.Empty;
    private string _sourceSignature = string.Empty;
    private string[] _ids = Array.Empty<string>();

    internal void Configure(IReadOnlyList<MappingSourceAddress> addresses, bool measure,
        IReadOnlyList<string> ids, string classIri, string sourceSignature)
    {
        _selection = JsonSerializer.Serialize(addresses);
        _measure = measure;
        _ids = ids.ToArray();
        _classIri = classIri;
        _sourceSignature = sourceSignature;
    }

    protected override void RegisterInputParams(GH_InputParamManager p) =>
        p.AddGenericParameter("Source", "Source", "Original source tree", GH_ParamAccess.tree);

    protected override void RegisterOutputParams(GH_OutputParamManager p)
    {
        p.AddGenericParameter("Selected", "Selected", "Committed members only", GH_ParamAccess.list);
        p.AddGenericParameter("Objects", "Objects", "Class and stable committed native identities", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        if (!da.GetDataTree<IGH_Goo>(0, out var tree)) return;
        try
        {
            if (MappingCanvasReader.DataSignature(tree) != _sourceSignature)
                throw new InvalidOperationException("Source changed after confirmation");
            var addresses = JsonSerializer.Deserialize<MappingSourceAddress[]>(_selection)
                ?? throw new InvalidOperationException("Missing selection");
            var values = new List<IGH_Goo>();
            var tolerance = Rhino.RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            var source = Enumerable.Range(0, tree.PathCount).ToDictionary(i => tree.Paths[i].ToString(),
                i => (IReadOnlyList<IGH_Goo>)tree.Branches[i], StringComparer.Ordinal);
            var selected = MappingSelection.Resolve(addresses, source, _measure);
            for (var i = 0; i < addresses.Length; i++)
            {
                var address = addresses[i];
                var branch = selected[i];
                if (_measure)
                {
                    values.Add(branch[0]);
                }
                else if (address.WholeBranch)
                {
                    var raw = branch.Select(g => MappingGeometry.Unwrap(g)).ToArray();
                    if (raw.Length == 1 && raw[0] is Rhino.Geometry.GeometryBase single)
                    {
                        values.Add(new GH_ObjectWrapper(single));
                    }
                    else if (raw.All(g => MappingGeometry.AsCurve(g) is not null))
                    {
                        var joined = Rhino.Geometry.Curve.JoinCurves(raw.Select(g => MappingGeometry.AsCurve(g)!).ToArray(), tolerance);
                        if (joined.Length != 1) throw new InvalidOperationException("Selected branch does not join into exactly one curve");
                        values.Add(new GH_ObjectWrapper(joined[0]));
                    }
                    else if (raw.All(g => MappingGeometry.AsBrep(g) is not null))
                    {
                        var joined = Rhino.Geometry.Brep.JoinBreps(raw.Select(g => MappingGeometry.AsBrep(g)!).ToArray(), tolerance);
                        if (joined is null || joined.Length != 1) throw new InvalidOperationException("Selected branch does not join into exactly one brep");
                        values.Add(new GH_ObjectWrapper(joined[0]));
                    }
                    else throw new InvalidOperationException("Selected branch is not one mapped geometry");
                }
                else
                {
                    values.Add(branch[0]);
                }
            }

            if (addresses.Length != _ids.Length) throw new InvalidOperationException("Selection identity count changed");
            da.SetDataList(0, values);
            da.SetDataList(1, _ids.Select(id => new MappingObjectReference { Iri = _classIri, NativeId = id }));
        }
        catch (Exception ex)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, $"Selection refused: {ex.GetType().Name}; remap the source");
            da.SetDataList(0, Array.Empty<IGH_Goo>());
        }
    }

    public override bool Write(GH_IO.Serialization.GH_IWriter writer)
    {
        writer.SetString("MappingSelection", _selection);
        writer.SetBoolean("MappingMeasure", _measure);
        writer.SetString("MappingClass", _classIri);
        writer.SetString("MappingSourceSignature", _sourceSignature);
        writer.SetString("MappingIds", JsonSerializer.Serialize(_ids));
        return base.Write(writer);
    }

    public override bool Read(GH_IO.Serialization.GH_IReader reader)
    {
        _selection = reader.GetString("MappingSelection");
        _measure = reader.GetBoolean("MappingMeasure");
        _classIri = reader.GetString("MappingClass");
        _sourceSignature = reader.GetString("MappingSourceSignature");
        _ids = JsonSerializer.Deserialize<string[]>(reader.GetString("MappingIds")) ?? Array.Empty<string>();
        return base.Read(reader);
    }
}
#endif
