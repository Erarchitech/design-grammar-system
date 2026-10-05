// v12-hexagonal-facade-01 — step 3a: rule quantities for calibration.
// Rhino 8 C# Script component. Lengths are converted from model units to meters
// via the document unit system, so the outputs are directly comparable to the
// thresholds in RULES.md (mirrored in the THRESHOLDS block below).
//
// One object = one branch. The script runs ONCE for the whole canvas: set the
// access of PB, HU, GU, PA, F, LZ to Tree (no type hint) and LT to Item.
//
// Inputs  (create these params on the component before pasting; names must match)
//   PB  Tree  Group B glass panels, one trimmed surface per branch        -> GlassPanel
//   HU  Tree  hexagonal units (floors 2+), outline lines of one unit/branch -> HexagonalUnit
//   GU  Tree  ground-floor units (pentagons), outline lines of one unit/branch -> GroundFloorUnit
//   PA  Tree  Group A bottom panels, one surface per branch                -> BottomTriangularPanel
//   F   Tree  facade geometry (flattened; anything with a bounding box)     -> Facade
//   LZ  Tree  level elevations in model units (flattened; optional — derived from HU if empty)
//   LT  Item  level clustering tolerance in model units (optional; default 50 mm)
// Outputs (one value per input branch, same branch paths as the input)
//   AR hasAspectRatio, PD hasPlanarityDeviationM, W hasWidthM   (per PB)
//   LO hasLevelOffsetM                                          (per HU)
//   HG hasOutlineGapCount, HV hasVertexCount                    (per HU)
//   GG hasOutlineGapCount, GV hasVertexCount                    (per GU)
//   VC hasVertexCount                                           (per PA)
//   H  hasHeightM                                               (one value)
//   Summary  min..max / p5 / median / p95 per quantity + violation counts at the thresholds
//   FailGeo  preview tree: {0} unreadable branches, {1}..{12} violators of R1..R12 (no R4)
//   Detail   one line per violator: rule, branch path, value
//
// Empty branches are not objects: they are skipped (and counted in Summary) and
// get no output value — clean the same trees before feeding OBJECT STATE.
// R4 (symmetry) was removed from the rule set on 2026-10-05; rule numbers are kept.
//
// hasOutlineGapCount = number of open pieces the branch's curves join into
// (0 = closed outline). Vertex counts are distinct corners after merging
// collinear segments; an open chain counts its end points as vertices.

#region Usings
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Rhino;
using Rhino.Geometry;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;
#endregion

public class Script_Instance : GH_ScriptInstance
{
  // ---------------------------------------------------------------- THRESHOLDS (RULES.md, calibrated on V1 2026-10-05)
  const double R1_ASPECT_MIN = 1.3;      // GlassPanel        hasAspectRatio        violation if <
  const double R2_ASPECT_MAX = 6.0;      // GlassPanel        hasAspectRatio        violation if >
  const double R3_LEVEL_MAX = 0.01;      // HexagonalUnit     hasLevelOffsetM       violation if > (control)
  const int    R5_TRI_VERTICES = 3;      // BottomTriangularPanel hasVertexCount    violation if !=
  const double R6_PLANARITY_MAX = 0.005; // GlassPanel        hasPlanarityDeviationM violation if >
  const double R7_WIDTH_MIN = 4.5;       // GlassPanel        hasWidthM             violation if <
  const double R8_HEIGHT_MAX = 120;      // Facade            hasHeightM            violation if >
  const int    R9_HEX_GAPS_MAX = 0;      // HexagonalUnit     hasOutlineGapCount    violation if >
  const int    R10_GROUND_GAPS_MAX = 0;  // GroundFloorUnit   hasOutlineGapCount    violation if >
  const int    R11_GROUND_VERTICES = 5;  // GroundFloorUnit   hasVertexCount        violation if !=
  const int    R12_HEX_VERTICES = 6;     // HexagonalUnit     hasVertexCount        violation if !=

  private void RunScript(
    DataTree<object> PB, DataTree<object> HU, DataTree<object> GU, DataTree<object> PA,
    DataTree<object> F, DataTree<object> LZ, object LT,
    ref object AR, ref object PD, ref object W,
    ref object LO, ref object HG, ref object HV,
    ref object GG, ref object GV, ref object VC,
    ref object H, ref object Summary, ref object FailGeo, ref object Detail)
  {
    var doc = RhinoDoc.ActiveDoc;
    _tol = doc.ModelAbsoluteTolerance;
    _k = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Meters);
    _errors.Clear();
    _failGeo = new DataTree<object>();
    _detail = new List<string>();

    // ---- Group B -> GlassPanel
    var pb = Read(PB, "PB");
    var ar = new List<double>(); var pd = new List<double>(); var w = new List<double>();
    foreach (var v in pb.Vertices)
    {
      if (v == null) { ar.Add(double.NaN); pd.Add(double.NaN); w.Add(double.NaN); continue; }
      double vert, hor;
      EdgeStats(v, out vert, out hor);
      ar.Add(vert / hor);
      w.Add(hor * _k);
      pd.Add(Planarity(v) * _k);
    }
    for (int i = 0; i < pb.Count; i++)
    {
      if (ar[i] < R1_ASPECT_MIN) Flag(1, pb, i, ar[i]);
      if (ar[i] > R2_ASPECT_MAX) Flag(2, pb, i, ar[i]);
      if (pd[i] > R6_PLANARITY_MAX) Flag(6, pb, i, pd[i]);
      if (w[i] < R7_WIDTH_MIN) Flag(7, pb, i, w[i]);
    }

    // ---- Facade bounding box (height)
    var bb = BoundingBox.Empty;
    foreach (var o in Flatten(F))
    {
      var g = o as GeometryBase;
      if (g != null) bb.Union(g.GetBoundingBox(true));
    }

    // ---- Hexagonal units (floors 2+)
    var hu = Read(HU, "HU");
    double lt = ToDouble(LT);
    if (!(lt > 0)) lt = 0.05 / _k;  // 50 mm expressed in model units
    var levels = Flatten(LZ).Select(ToDouble).Where(z => !double.IsNaN(z)).ToList();
    string levelSource;
    if (levels.Count > 0) levelSource = "LZ input, " + levels.Count + " levels";
    else
    {
      levels = ClusterLevels(hu.Vertices.Where(v => v != null).SelectMany(v => v).Select(p => p.Z), lt);
      levelSource = "DERIVED from HU vertex Z (tol " + Fmt(lt * _k) + " m), " + levels.Count + " levels — supply LZ for a real check";
    }
    var lo = new List<double>();
    for (int i = 0; i < hu.Count; i++)
    {
      var v = hu.Vertices[i];
      lo.Add(v == null || levels.Count == 0 ? double.NaN : v.Max(p => levels.Min(z => Math.Abs(p.Z - z))) * _k);
    }
    var hv = hu.VertexCounts();
    for (int i = 0; i < hu.Count; i++)
    {
      if (lo[i] > R3_LEVEL_MAX) Flag(3, hu, i, lo[i], "top Z " + Fmt(hu.Vertices[i].Max(p => p.Z) * _k));
      if (hu.Gaps[i] > R9_HEX_GAPS_MAX) Flag(9, hu, i, hu.Gaps[i]);
      if (hv[i] >= 0 && hv[i] != R12_HEX_VERTICES) Flag(12, hu, i, hv[i]);
    }
    var huZ = hu.Vertices.Where(v => v != null).SelectMany(v => v).Select(p => p.Z * _k).ToList();

    // ---- Ground-floor units (pentagons)
    var gu = Read(GU, "GU");
    var gv = gu.VertexCounts();
    for (int i = 0; i < gu.Count; i++)
    {
      if (gu.Gaps[i] > R10_GROUND_GAPS_MAX) Flag(10, gu, i, gu.Gaps[i]);
      if (gv[i] >= 0 && gv[i] != R11_GROUND_VERTICES) Flag(11, gu, i, gv[i]);
    }

    // ---- Group A -> BottomTriangularPanel
    var pa = Read(PA, "PA");
    var vc = pa.VertexCounts();
    for (int i = 0; i < pa.Count; i++)
      if (vc[i] >= 0 && vc[i] != R5_TRI_VERTICES) Flag(5, pa, i, vc[i]);

    // ---- Facade height
    double h = bb.IsValid ? (bb.Max.Z - bb.Min.Z) * _k : double.NaN;
    if (h > R8_HEIGHT_MAX) _detail.Add("R8 Facade = " + Fmt(h));

    AR = ToTree(pb.Paths, ar); PD = ToTree(pb.Paths, pd); W = ToTree(pb.Paths, w);
    LO = ToTree(hu.Paths, lo);
    HG = ToTree(hu.Paths, hu.Gaps); HV = ToTree(hu.Paths, hv);
    GG = ToTree(gu.Paths, gu.Gaps); GV = ToTree(gu.Paths, gv);
    VC = ToTree(pa.Paths, vc);
    H = h;
    FailGeo = _failGeo;
    Detail = _detail;

    // ---- Summary
    var s = new StringBuilder();
    s.AppendLine("model units: " + doc.ModelUnitSystem + "  (x" + Fmt(_k) + " -> m)");
    s.AppendLine("GlassPanel  n=" + pb.Count + Skipped(pb) + "   outline vertices: " + Distribution(pb.Vertices));
    s.AppendLine("  hasAspectRatio          " + Range(ar) + "   R1 <" + Fmt(R1_ASPECT_MIN) + ": " + Count(ar, x => x < R1_ASPECT_MIN) + "   R2 >" + Fmt(R2_ASPECT_MAX) + ": " + Count(ar, x => x > R2_ASPECT_MAX));
    s.AppendLine("  hasPlanarityDeviationM  " + Range(pd) + "   R6 >" + Fmt(R6_PLANARITY_MAX) + ": " + Count(pd, x => x > R6_PLANARITY_MAX));
    s.AppendLine("  hasWidthM               " + Range(w) + "   R7 <" + Fmt(R7_WIDTH_MIN) + ": " + Count(w, x => x < R7_WIDTH_MIN));
    s.AppendLine("HexagonalUnit  n=" + hu.Count + Skipped(hu) + "   outline vertices: " + Distribution(hu.Vertices));
    s.AppendLine("  levels: " + levelSource + "   level Z " + Range(levels.Select(z => z * _k).ToList(), false) + "   HU vertex Z " + Range(huZ, false));
    s.AppendLine("  hasLevelOffsetM         " + Range(lo) + "   R3 >" + Fmt(R3_LEVEL_MAX) + ": " + Count(lo, x => x > R3_LEVEL_MAX) + "  (control)");
    s.AppendLine("  hasOutlineGapCount      " + IntDistribution(hu.Gaps) + "   R9 >" + R9_HEX_GAPS_MAX + ": " + hu.Gaps.Count(x => x > R9_HEX_GAPS_MAX));
    s.AppendLine("  hasVertexCount          " + IntDistribution(hv) + "   R12 !=" + R12_HEX_VERTICES + ": " + hv.Count(x => x >= 0 && x != R12_HEX_VERTICES));
    s.AppendLine("GroundFloorUnit  n=" + gu.Count + Skipped(gu));
    s.AppendLine("  hasOutlineGapCount      " + IntDistribution(gu.Gaps) + "   R10 >" + R10_GROUND_GAPS_MAX + ": " + gu.Gaps.Count(x => x > R10_GROUND_GAPS_MAX));
    s.AppendLine("  hasVertexCount          " + IntDistribution(gv) + "   R11 !=" + R11_GROUND_VERTICES + ": " + gv.Count(x => x >= 0 && x != R11_GROUND_VERTICES));
    s.AppendLine("BottomTriangularPanel  n=" + pa.Count + Skipped(pa));
    s.AppendLine("  hasVertexCount          " + IntDistribution(vc) + "   R5 !=" + R5_TRI_VERTICES + ": " + vc.Count(x => x >= 0 && x != R5_TRI_VERTICES) + "  (control)");
    s.AppendLine("Facade");
    s.AppendLine("  hasHeightM              " + Fmt(h) + "   R8 >" + Fmt(R8_HEIGHT_MAX) + ": " + (h > R8_HEIGHT_MAX ? "VIOLATED" : "ok"));
    if (_errors.Count > 0)
    {
      s.AppendLine("errors (" + _errors.Count + "):");
      foreach (var e in _errors.Take(20)) s.AppendLine("  " + e);
      if (_errors.Count > 20) s.AppendLine("  ... " + (_errors.Count - 20) + " more");
    }
    Summary = s.ToString();
  }

  double _tol, _k;
  readonly List<string> _errors = new List<string>();
  DataTree<object> _failGeo;
  List<string> _detail;

  // One input tree read as objects: branch path, corner points, open-piece count.
  class ObjectSet
  {
    public string Tag;
    public readonly List<GH_Path> Paths = new List<GH_Path>();
    public readonly List<List<Point3d>> Vertices = new List<List<Point3d>>();
    public readonly List<int> Gaps = new List<int>();
    public readonly List<bool> Ordered = new List<bool>();   // corners in outline order
    public int Empty;
    public int Count { get { return Paths.Count; } }
    public List<int> VertexCounts() { return Vertices.Select(v => v == null ? -1 : v.Count).ToList(); }
  }

  static string Skipped(ObjectSet set)
  {
    return set.Empty > 0 ? " (" + set.Empty + " empty branches skipped)" : "";
  }

  void Flag(int rule, ObjectSet set, int i, double value, string note = null)
  {
    _detail.Add("R" + rule + " " + set.Tag + set.Paths[i] + " = " + Fmt(value) + (note == null ? "" : "   " + note));
    var v = set.Vertices[i];
    if (v != null && v.Count > 1) _failGeo.Add(ToCurve(v, set.Gaps[i] == 0), new GH_Path(rule));
  }

  static Curve ToCurve(List<Point3d> v, bool closed)
  {
    var pl = new Polyline(v);
    if (closed) pl.Add(v[0]);
    return new PolylineCurve(pl);
  }

  // ---------------------------------------------------------------- tree plumbing

  static IEnumerable<object> Flatten(DataTree<object> tree)
  {
    if (tree == null) yield break;
    foreach (var o in tree.AllData()) { var u = Unwrap(o); if (u != null) yield return u; }
  }

  static DataTree<T> ToTree<T>(List<GH_Path> paths, List<T> values)
  {
    var t = new DataTree<T>();
    for (int i = 0; i < paths.Count; i++) t.Add(values[i], paths[i]);
    return t;
  }

  ObjectSet Read(DataTree<object> tree, string tag)
  {
    var set = new ObjectSet { Tag = tag };
    if (tree == null) return set;
    foreach (var path in tree.Paths)
    {
      var items = tree.Branch(path).Select(Unwrap).Where(o => o != null).ToList();
      if (items.Count == 0) { set.Empty++; continue; }
      string err; int gaps; bool ordered;
      var v = BranchVertices(items, out err, out gaps, out ordered);
      if (v != null && v.Count < 3) { err = "only " + v.Count + " vertices"; v = null; }
      if (v == null)
      {
        _errors.Add(tag + path + ": " + (err ?? "no outline"));
        foreach (var g in items.OfType<GeometryBase>()) _failGeo.Add(g, new GH_Path(0));
        foreach (var ln in items.OfType<Line>()) _failGeo.Add(new LineCurve(ln), new GH_Path(0));
      }
      set.Paths.Add(path);
      set.Vertices.Add(v);
      set.Gaps.Add(gaps);
      set.Ordered.Add(v != null && ordered);
    }
    return set;
  }

  // A branch is one object: one surface/brep/mesh, one curve, or several curves that
  // join into the outline. Several joined pieces (an outline with gaps) yield the
  // de-duplicated union of their corners — order-free, which is all the hexagonal
  // measures need; ordered corners come only from a single piece.
  List<Point3d> BranchVertices(List<object> items, out string err, out int gaps, out bool ordered)
  {
    err = null; gaps = 0; ordered = true;
    if (items.Count == 0) { err = "empty branch"; return null; }

    var curves = items.Select(AsCurve).Where(c => c != null).ToList();
    if (curves.Count == items.Count)
    {
      var pieces = curves.Count == 1 ? curves.ToArray() : Curve.JoinCurves(curves, Math.Max(_tol * 10, 0.001 / _k));  // 1 mm join gap
      if (pieces == null || pieces.Length == 0) { err = curves.Count + " curves failed to join"; return null; }
      gaps = pieces.Count(c => !c.IsClosed);
      if (pieces.Length == 1) return CurveVertices(pieces[0]);
      ordered = false;
      var union = new List<Point3d>();
      foreach (var piece in pieces)
        foreach (var p in CurveVertices(piece))
          if (!union.Any(q => q.DistanceTo(p) <= _tol)) union.Add(p);
      return union;
    }

    if (items.Count == 1 && items[0] is Mesh)
    {
      var naked = ((Mesh)items[0]).GetNakedEdges();
      if (naked != null && naked.Length > 0) return Clean(naked.OrderByDescending(p => p.Length).First());
      err = "mesh without naked edges"; return null;
    }

    var breps = items.Select(AsBrep).Where(b => b != null).ToList();
    if (breps.Count == items.Count)
    {
      var brep = breps.Count == 1 ? breps[0] : null;
      if (brep == null)
      {
        var joined = Brep.JoinBreps(breps, _tol);
        if (joined == null || joined.Length != 1) { err = breps.Count + " surfaces do not join into one brep"; return null; }
        brep = joined[0];
      }
      var loop = LargestFaceLoop(brep);
      if (loop == null) { err = "brep without faces"; return null; }
      return CurveVertices(loop);
    }

    err = items.Count + " items of mixed or unsupported types (" +
          string.Join(", ", items.Select(o => o.GetType().Name).Distinct()) + ")";
    return null;
  }

  static object Unwrap(object o)
  {
    var goo = o as IGH_Goo;
    return goo != null ? goo.ScriptVariable() : o;
  }

  static Curve AsCurve(object o)
  {
    if (o is Curve) return (Curve)o;
    if (o is Line) return new LineCurve((Line)o);
    if (o is Polyline) return ((Polyline)o).ToNurbsCurve();
    return null;
  }

  static Brep AsBrep(object o)
  {
    if (o is Brep) return (Brep)o;
    if (o is Extrusion) return ((Extrusion)o).ToBrep();
    if (o is Surface) return ((Surface)o).ToBrep();
    return null;
  }

  // ---------------------------------------------------------------- geometry

  List<Point3d> CurveVertices(Curve c)
  {
    Polyline pl;
    if (!c.TryGetPolyline(out pl))
    {
      var segs = c.DuplicateSegments();
      if (segs != null && segs.Length > 1)
      {
        pl = new Polyline(segs.Select(sg => sg.PointAtStart));
        pl.Add(segs[segs.Length - 1].PointAtEnd);
      }
      else
      {
        // single smooth span: corners = G1 discontinuities
        var pts = new List<Point3d> { c.PointAtStart };
        double t = c.Domain.Min, tn;
        while (c.GetNextDiscontinuity(Continuity.G1_continuous, t, c.Domain.Max, out tn)) { pts.Add(c.PointAt(tn)); t = tn; }
        pts.Add(c.PointAtEnd);
        pl = new Polyline(pts);
      }
    }
    return Clean(pl);
  }

  static Curve LargestFaceLoop(Brep b)
  {
    if (b == null || b.Faces.Count == 0) return null;
    BrepFace best = null; double bestArea = -1;
    foreach (var f in b.Faces)
    {
      var amp = AreaMassProperties.Compute(f);
      double a = amp == null ? 0 : amp.Area;
      if (a > bestArea) { bestArea = a; best = f; }
    }
    return best.OuterLoop.To3dCurve();
  }

  // Corner list: short and collinear segments removed, closing duplicate dropped.
  List<Point3d> Clean(Polyline src)
  {
    var p = new Polyline(src);
    bool closed = p.Count > 2 && p[0].DistanceTo(p[p.Count - 1]) <= _tol;
    p.DeleteShortSegments(_tol);
    p.MergeColinearSegments(RhinoMath.ToRadians(0.5), closed);
    var pts = p.ToList();
    if (closed && pts.Count > 1 && pts[0].DistanceTo(pts[pts.Count - 1]) <= _tol) pts.RemoveAt(pts.Count - 1);
    return pts;
  }

  // Mean "vertical" and "horizontal" edge length. For quads the opposite-edge pair
  // that is steeper on average is vertical (robust to slanted cells); otherwise
  // each edge is classified by its angle to world Z (45 deg split).
  static void EdgeStats(List<Point3d> v, out double vert, out double hor)
  {
    var len = new List<double>(); var steep = new List<double>();
    for (int i = 0; i < v.Count; i++)
    {
      var d = v[(i + 1) % v.Count] - v[i];
      len.Add(d.Length);
      steep.Add(d.Length > 0 ? Math.Abs(d.Z) / d.Length : 0);
    }
    if (v.Count == 4)
    {
      bool evenVertical = steep[0] + steep[2] >= steep[1] + steep[3];
      vert = evenVertical ? (len[0] + len[2]) / 2 : (len[1] + len[3]) / 2;
      hor = evenVertical ? (len[1] + len[3]) / 2 : (len[0] + len[2]) / 2;
      return;
    }
    double cut = Math.Cos(RhinoMath.ToRadians(45));
    var vl = new List<double>(); var hl = new List<double>();
    for (int i = 0; i < len.Count; i++) (steep[i] >= cut ? vl : hl).Add(len[i]);
    vert = vl.Count > 0 ? vl.Average() : double.NaN;
    hor = hl.Count > 0 ? hl.Average() : double.NaN;
  }

  static double Planarity(List<Point3d> v)
  {
    if (v.Count < 4) return 0;
    Plane pl;
    if (Plane.FitPlaneToPoints(v, out pl) != PlaneFitResult.Success) return double.NaN;
    return v.Max(p => Math.Abs(pl.DistanceTo(p)));
  }

  static List<double> ClusterLevels(IEnumerable<double> zs, double tol)
  {
    var sorted = zs.OrderBy(z => z).ToList();
    var levels = new List<double>();
    var group = new List<double>();
    foreach (var z in sorted)
    {
      if (group.Count > 0 && z - group[group.Count - 1] > tol) { levels.Add(group.Average()); group.Clear(); }
      group.Add(z);
    }
    if (group.Count > 0) levels.Add(group.Average());
    return levels;
  }

  // ---------------------------------------------------------------- formatting

  static double ToDouble(object o)
  {
    o = Unwrap(o);
    if (o == null) return double.NaN;
    try { return Convert.ToDouble(o, CultureInfo.InvariantCulture); } catch { return double.NaN; }
  }

  static string Fmt(double x)
  {
    return double.IsNaN(x) ? "NaN" : x.ToString("0.#####", CultureInfo.InvariantCulture);
  }

  static string Range(List<double> xs, bool quantiles = true)
  {
    var ok = xs.Where(x => !double.IsNaN(x) && !double.IsInfinity(x)).OrderBy(x => x).ToList();
    int bad = xs.Count - ok.Count;
    if (ok.Count == 0) return "no values" + (bad > 0 ? " (" + bad + " NaN)" : "");
    var r = Fmt(ok[0]) + " .. " + Fmt(ok[ok.Count - 1]);
    if (quantiles) r += "  [p5 " + Fmt(Q(ok, 0.05)) + " | med " + Fmt(Q(ok, 0.5)) + " | p95 " + Fmt(Q(ok, 0.95)) + "]";
    return r + (bad > 0 ? "  (" + bad + " NaN)" : "");
  }

  // nearest-rank quantile of an ascending list
  static double Q(List<double> sorted, double q)
  {
    int i = (int)Math.Ceiling(q * sorted.Count) - 1;
    return sorted[Math.Max(0, Math.Min(sorted.Count - 1, i))];
  }

  static int Count(List<double> xs, Func<double, bool> pred)
  {
    return xs.Count(x => !double.IsNaN(x) && pred(x));
  }

  // "4x120, 5x4" — corner counts of the outlines; unreadable branches show as "failed".
  static string Distribution(List<List<Point3d>> outlines)
  {
    return IntDistribution(outlines.Select(v => v == null ? -1 : v.Count).ToList());
  }

  static string IntDistribution(List<int> xs)
  {
    if (xs.Count == 0) return "none";
    return string.Join(", ", xs.GroupBy(x => x).OrderBy(g => g.Key)
      .Select(g => (g.Key < 0 ? "failed" : g.Key.ToString()) + "x" + g.Count()));
  }
}
