#if GRASSHOPPER_SDK
using Grasshopper.Kernel.Types;
using Rhino;
using Rhino.Geometry;

namespace DG.Grasshopper.Mapping;

/// <summary>Class-agnostic features of one element and the geometry drawn for it.</summary>
internal sealed class DescribedElement
{
    public string Kind { get; set; } = string.Empty;

    public GeometryBase? Preview { get; set; }

    public Dictionary<string, object> Geometry { get; } = new(StringComparer.Ordinal);

    public Dictionary<string, object> Properties { get; } = new(StringComparer.Ordinal);
}

/// <summary>
/// Geometry features for automatic mapping (Phase 1303), carried over from the prototype
/// script component (test/v12-hexagonal-facade-01/gh-mapping-intake.cs) and
/// gh-measure-rules.cs: outlines give vertex and gap counts and level offsets, panels give
/// vertex count, planarity, width, height and aspect ratio, solids give their height.
/// Units: metres. Features only — never a class.
/// </summary>
internal sealed class MappingGeometry
{
    private readonly double _tol;
    private readonly double _k;
    private readonly IReadOnlyList<double> _levels;

    public MappingGeometry(double tolerance, double metresPerUnit, IReadOnlyList<double> levels)
    {
        _tol = tolerance > 0 ? tolerance : 0.001;
        _k = metresPerUnit > 0 ? metresPerUnit : 1.0;
        _levels = levels;
    }

    public static object? Unwrap(object? o) => o is IGH_Goo goo ? goo.ScriptVariable() : o;

    public static bool IsGeometry(object? o)
    {
        var u = Unwrap(o);
        return AsCurve(u) is not null || AsBrep(u) is not null || u is Mesh;
    }

    public bool TryDescribe(IReadOnlyList<object> rawItems, out DescribedElement element, out string error)
    {
        element = new DescribedElement();
        error = string.Empty;
        var items = rawItems.Select(Unwrap).Where(o => o is not null).Cast<object>().ToList();
        if (items.Count == 0)
        {
            error = "empty";
            return false;
        }

        try
        {
            var curves = items.Select(AsCurve).Where(c => c is not null).Cast<Curve>().ToList();
            if (curves.Count == items.Count)
            {
                DescribeCurves(curves, element);
                return true;
            }

            var breps = items.Select(AsBrep).Where(b => b is not null).Cast<Brep>().ToList();
            if (breps.Count == items.Count)
            {
                var brep = breps.Count == 1 ? breps[0] : (Brep.JoinBreps(breps, _tol) ?? Array.Empty<Brep>()).FirstOrDefault();
                if (brep is null)
                {
                    error = "surfaces do not join into one brep";
                    return false;
                }

                if (brep.IsSolid)
                {
                    DescribeSolid(brep, element);
                }
                else
                {
                    DescribePanel(brep, null, element);
                }

                return true;
            }

            if (items.Count == 1 && items[0] is Mesh mesh)
            {
                DescribePanel(null, mesh, element);
                return true;
            }

            error = "unsupported item types";
            return false;
        }
        catch (Exception ex)
        {
            error = ex.GetType().Name;
            return false;
        }
    }

    private void DescribeCurves(List<Curve> curves, DescribedElement e)
    {
        var pieces = curves.Count == 1 ? curves.ToArray() : Curve.JoinCurves(curves, Math.Max(_tol * 10, 0.001 / _k));
        if (pieces is null || pieces.Length == 0)
        {
            throw new InvalidOperationException("curves do not join");
        }

        var gaps = pieces.Count(c => !c.IsClosed);
        var v = new List<Point3d>();
        foreach (var piece in pieces)
        {
            foreach (var p in CurveVertices(piece))
            {
                if (!v.Any(q => q.DistanceTo(p) <= _tol))
                {
                    v.Add(p);
                }
            }
        }

        if (v.Count == 0)
        {
            throw new InvalidOperationException("curve without vertices");
        }

        e.Kind = "curve";
        e.Preview = pieces.Length == 1 ? pieces[0] : new PolylineCurve(new Polyline(v.Concat(new[] { v[0] })));
        e.Geometry["kind"] = "curve";
        e.Geometry["vertexCount"] = v.Count;
        e.Geometry["gapCount"] = gaps;
        e.Geometry["closed"] = gaps == 0;
        e.Geometry["zMinM"] = R(v.Min(p => p.Z) * _k);
        e.Geometry["zMaxM"] = R(v.Max(p => p.Z) * _k);
        e.Properties["hasVertexCount"] = v.Count;
        e.Properties["hasGapCount"] = gaps;
        e.Properties["hasOutlineGapCount"] = gaps;
        if (_levels.Count > 0)
        {
            e.Properties["hasLevelOffsetM"] = R(v.Max(p => _levels.Min(z => Math.Abs(p.Z - z))) * _k);
        }
    }

    private void DescribeSolid(Brep brep, DescribedElement e)
    {
        var bb = brep.GetBoundingBox(true);
        e.Kind = "solid";
        e.Preview = brep;
        e.Geometry["kind"] = "solid";
        e.Geometry["vertexCount"] = brep.Vertices.Count;
        e.Geometry["closed"] = true;
        e.Geometry["zMinM"] = R(bb.Min.Z * _k);
        e.Geometry["zMaxM"] = R(bb.Max.Z * _k);
        e.Geometry["heightM"] = R((bb.Max.Z - bb.Min.Z) * _k);
        e.Geometry["widthM"] = R(Math.Max(bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y) * _k);
        e.Properties["hasHeightM"] = R((bb.Max.Z - bb.Min.Z) * _k);
        e.Properties["hasTotalHeightM"] = R((bb.Max.Z - bb.Min.Z) * _k);
    }

    private void DescribePanel(Brep? brep, Mesh? mesh, DescribedElement e)
    {
        List<Point3d>? corners = null;
        if (brep is not null)
        {
            var loop = LargestFaceLoop(brep) ?? throw new InvalidOperationException("brep without faces");
            corners = CurveVertices(loop);
            e.Preview = brep;
            var amp = AreaMassProperties.Compute(brep);
            if (amp is not null)
            {
                e.Geometry["areaM2"] = R(amp.Area * _k * _k);
            }
        }
        else if (mesh is not null)
        {
            var naked = mesh.GetNakedEdges();
            if (naked is null || naked.Length == 0)
            {
                throw new InvalidOperationException("mesh without naked edges");
            }

            corners = Clean(naked.OrderByDescending(p => p.Length).First());
            e.Preview = mesh;
        }

        if (corners is null || corners.Count == 0)
        {
            throw new InvalidOperationException("unsupported item types");
        }

        e.Kind = brep is not null ? "surface" : "mesh";
        e.Geometry["kind"] = e.Kind;
        e.Geometry["vertexCount"] = corners.Count;
        e.Geometry["closed"] = true;
        e.Geometry["zMinM"] = R(corners.Min(p => p.Z) * _k);
        e.Geometry["zMaxM"] = R(corners.Max(p => p.Z) * _k);
        e.Properties["hasVertexCount"] = corners.Count;
        EdgeStats(corners, out var vert, out var hor);
        var planarity = Planarity(corners) * _k;
        if (IsFinite(planarity))
        {
            e.Geometry["planarityDeviationM"] = R(planarity);
            e.Properties["hasPlanarityDeviationM"] = R(planarity);
        }

        if (IsFinite(hor))
        {
            e.Geometry["widthM"] = R(hor * _k);
            e.Properties["hasWidthM"] = R(hor * _k);
        }

        if (IsFinite(vert))
        {
            e.Geometry["heightM"] = R(vert * _k);
        }

        if (IsFinite(vert) && IsFinite(hor) && hor > 0)
        {
            e.Properties["hasAspectRatio"] = R(vert / hor);
        }
    }

    public static Curve? AsCurve(object? o) => o switch
    {
        Curve c => c,
        Line l => new LineCurve(l),
        Polyline p => p.ToNurbsCurve(),
        Rectangle3d r => r.ToNurbsCurve(),
        Circle c => new ArcCurve(c),
        Arc a => new ArcCurve(a),
        _ => null,
    };

    public static Brep? AsBrep(object? o) => o switch
    {
        Brep b => b,
        Extrusion x => x.ToBrep(),
        Surface s => s.ToBrep(),
        Box b => b.ToBrep(),
        _ => null,
    };

    private List<Point3d> CurveVertices(Curve c)
    {
        if (!c.TryGetPolyline(out var pl))
        {
            var segs = c.DuplicateSegments();
            if (segs is not null && segs.Length > 1)
            {
                pl = new Polyline(segs.Select(sg => sg.PointAtStart));
                pl.Add(segs[^1].PointAtEnd);
            }
            else
            {
                var pts = new List<Point3d> { c.PointAtStart };
                var t = c.Domain.Min;
                while (c.GetNextDiscontinuity(Continuity.G1_continuous, t, c.Domain.Max, out var tn))
                {
                    pts.Add(c.PointAt(tn));
                    t = tn;
                }

                pts.Add(c.PointAtEnd);
                pl = new Polyline(pts);
            }
        }

        return Clean(pl);
    }

    private static Curve? LargestFaceLoop(Brep b)
    {
        if (b.Faces.Count == 0)
        {
            return null;
        }

        BrepFace? best = null;
        var bestArea = -1.0;
        foreach (var f in b.Faces)
        {
            var amp = AreaMassProperties.Compute(f);
            var a = amp?.Area ?? 0;
            if (a > bestArea)
            {
                bestArea = a;
                best = f;
            }
        }

        return best?.OuterLoop.To3dCurve();
    }

    private List<Point3d> Clean(Polyline src)
    {
        var p = new Polyline(src);
        var closed = p.Count > 2 && p[0].DistanceTo(p[p.Count - 1]) <= _tol;
        p.DeleteShortSegments(_tol);
        p.MergeColinearSegments(RhinoMath.ToRadians(0.5), closed);
        var pts = p.ToList();
        if (closed && pts.Count > 1 && pts[0].DistanceTo(pts[^1]) <= _tol)
        {
            pts.RemoveAt(pts.Count - 1);
        }

        return pts;
    }

    private static void EdgeStats(List<Point3d> v, out double vert, out double hor)
    {
        var len = new List<double>();
        var steep = new List<double>();
        for (var i = 0; i < v.Count; i++)
        {
            var d = v[(i + 1) % v.Count] - v[i];
            len.Add(d.Length);
            steep.Add(d.Length > 0 ? Math.Abs(d.Z) / d.Length : 0);
        }

        if (v.Count == 4)
        {
            var evenVertical = steep[0] + steep[2] >= steep[1] + steep[3];
            vert = evenVertical ? (len[0] + len[2]) / 2 : (len[1] + len[3]) / 2;
            hor = evenVertical ? (len[1] + len[3]) / 2 : (len[0] + len[2]) / 2;
            return;
        }

        var cut = Math.Cos(RhinoMath.ToRadians(45));
        var vl = new List<double>();
        var hl = new List<double>();
        for (var i = 0; i < len.Count; i++)
        {
            (steep[i] >= cut ? vl : hl).Add(len[i]);
        }

        vert = vl.Count > 0 ? vl.Average() : double.NaN;
        hor = hl.Count > 0 ? hl.Average() : double.NaN;
    }

    private static double Planarity(List<Point3d> v)
    {
        if (v.Count < 4)
        {
            return 0;
        }

        if (Plane.FitPlaneToPoints(v, out var pl) != PlaneFitResult.Success)
        {
            return double.NaN;
        }

        return v.Max(p => Math.Abs(pl.DistanceTo(p)));
    }

    private static bool IsFinite(double x) => !double.IsNaN(x) && !double.IsInfinity(x);

    private static double R(double x) => Math.Round(x, 6);
}
#endif
