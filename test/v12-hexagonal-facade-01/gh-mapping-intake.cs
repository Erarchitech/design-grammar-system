// v12-hexagonal-facade-01 — Phase 1303 MVP slice: DG MAPPING (prototype script component).
// Rhino 8 C# Script component (.NET 7 runtime). Sends class-agnostic element descriptors of
// the facade streams to DG (POST /mapping/sessions), shows the mapping state as preview
// colours and returns the geometry partitioned by class for the OBJECT STATE components.
// Contract: .planning/phases/1303-pravilo-gh-obekt/1303-API-CONTRACT.md
//
// One object = one branch (as in gh-measure-rules.cs). Create these inputs before pasting
// (names must match; Tree access, no type hint, unless "Item" or "List" is written):
//   HU, GU, PB, PA   Tree  facade streams (outline curves or one surface per branch)
//   F                Tree  facade geometry (flattened; one bounding box = one element)
//   LZ               Tree  level elevations in model units (optional; for hasLevelOffsetM)
//   OntoClasses      List  METAGRAPH class objects (optional; matched to classes by name/IRI)
//   Classes          List  class labels in the order of your OBJECT STATE components (optional)
//   GuAsHu           Item  bool  — true: GU branches are sent as source "HU" (reproduces F5)
//   DefinitionKey    Item  string — part of the native ids, e.g. "facade-v1"
//   Project          Item  string — DG project, e.g. "v12-hexagonal-facade-01"
//   Url              Item  string — data-service base URL (default http://localhost:8000)
//   Token            Item  string — wire CONNECTOR.Session directly (never through a Panel)
//   Label            Item  string — session label, e.g. "act1-cold-start"
//   SessionId        Item  string — optional: read this session on Refresh instead of the last one
//   Run, Refresh, Apply, DryRun   Item  bool — use Buttons; HTTP runs only on a rising edge
// Outputs (a component cannot have an input and an output with the same name):
//   SessionIdOut, Summary, Questions       session id, summary text, open question count
//   Geometry, Colour, State, Roles, NativeId   one entry per element, same order (Custom Preview)
//   ByClass       Tree: branch {k} = geometry of the elements whose applied roles contain class k,
//                 in the original stream/branch order (keeps PROPERTY STATE pairing by position)
//   ClassNames    labels aligned with ByClass branches
//   ClassObjects  OntoClasses items aligned with ByClass branches (matched by label or IRI)
//   Log           descriptors JSON on DryRun, HTTP status / error code otherwise (never the token)
//
// Features are computed for every element from its geometry only; the stream name is sent as
// `source` (name evidence), never as a class. Panel measures (aspect ratio, width, planarity)
// are computed for surfaces, outline measures (gaps, level offset) for curves; the facade box
// carries its total height. Units: metres.

#region Usings
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using Rhino;
using Rhino.Geometry;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;
#endregion

public class Script_Instance : GH_ScriptInstance
{
  static readonly HttpClient Http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };

  static readonly Dictionary<string, Color> Palette = new Dictionary<string, Color>
  {
    { "confirmed", ColorTranslator.FromHtml("#2E7D32") },
    { "auto", ColorTranslator.FromHtml("#1565C0") },
    { "suggested", ColorTranslator.FromHtml("#F9A825") },
    { "ambiguous", ColorTranslator.FromHtml("#E65100") },
    { "unmapped", ColorTranslator.FromHtml("#9E9E9E") },
  };

  bool _prevRun, _prevRefresh, _prevApply;
  string _sessionJson, _applyJson, _sessionId, _lastLog = "";

  private void RunScript(
    DataTree<object> HU, DataTree<object> GU, DataTree<object> PB, DataTree<object> PA,
    DataTree<object> F, DataTree<object> LZ, List<object> OntoClasses, List<string> Classes,
    bool GuAsHu, string DefinitionKey, string Project, string Url, string Token, string Label,
    string SessionId, bool Run, bool Refresh, bool Apply, bool DryRun,
    ref object SessionIdOut, ref object Summary, ref object Questions,
    ref object Geometry, ref object Colour, ref object State, ref object Roles, ref object NativeId,
    ref object ByClass, ref object ClassNames, ref object ClassObjects, ref object Log)
  {
    var doc = RhinoDoc.ActiveDoc;
    _tol = doc.ModelAbsoluteTolerance;
    _k = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Meters);
    _errors.Clear();

    string key = string.IsNullOrWhiteSpace(DefinitionKey) ? "facade" : DefinitionKey.Trim();
    string url = string.IsNullOrWhiteSpace(Url) ? "http://localhost:8000" : Url.Trim().TrimEnd('/');
    var levels = Flatten(LZ).Select(ToDouble).Where(z => !double.IsNaN(z)).ToList();

    // ---- elements (class-agnostic descriptors)
    var elements = new List<Element>();
    ReadStream(HU, "HU", "HU", key, levels, elements);
    ReadStream(GU, "GU", GuAsHu ? "HU" : "GU", key, levels, elements);
    ReadStream(PB, "PB", "PB", key, levels, elements);
    ReadStream(PA, "PA", "PA", key, levels, elements);
    ReadFacade(F, key, elements);

    // ---- HTTP on rising edges only
    var log = new StringBuilder();
    if (DryRun)
    {
      log.AppendLine(SerializeDescriptors(elements.Take(50), true));
      if (elements.Count > 50) log.AppendLine("... " + (elements.Count - 50) + " more elements");
    }
    try
    {
      if (Run && !_prevRun)
      {
        if (DryRun) log.AppendLine("DryRun is on: no request sent.");
        else
        {
          var body = "{\"project\":" + JsonSerializer.Serialize(Project ?? "") +
                     ",\"platform\":\"grasshopper\",\"label\":" + JsonSerializer.Serialize(string.IsNullOrWhiteSpace(Label) ? key : Label) +
                     ",\"elements\":" + SerializeDescriptors(elements, false) + "}";
          var text = Send(HttpMethod.Post, url + "/mapping/sessions", body, Token, log);
          if (text != null) { _sessionJson = text; _applyJson = null; _sessionId = ReadString(text, "sessionId"); }
        }
      }
      if (Refresh && !_prevRefresh && !DryRun)
      {
        var sid = string.IsNullOrWhiteSpace(SessionId) ? _sessionId : SessionId.Trim();
        if (string.IsNullOrEmpty(sid)) log.AppendLine("Refresh: no session yet (press Run or set SessionId).");
        else
        {
          var text = Send(HttpMethod.Get, url + "/mapping/sessions/" + Uri.EscapeDataString(sid) + "?project=" + Uri.EscapeDataString(Project ?? ""), null, Token, log);
          if (text != null) { _sessionJson = text; _sessionId = sid; }
        }
      }
      if (Apply && !_prevApply && !DryRun)
      {
        if (string.IsNullOrEmpty(_sessionId)) log.AppendLine("Apply: no session yet.");
        else
        {
          var text = Send(HttpMethod.Post, url + "/mapping/sessions/" + Uri.EscapeDataString(_sessionId) + "/apply",
                          "{\"project\":" + JsonSerializer.Serialize(Project ?? "") + "}", Token, log);
          if (text != null) _applyJson = text;
        }
      }
    }
    catch (Exception ex)
    {
      log.AppendLine("error: " + ex.GetType().Name + ": " + ex.Message);
    }
    _prevRun = Run; _prevRefresh = Refresh; _prevApply = Apply;
    if (log.Length > 0) _lastLog = log.ToString();

    // ---- session result -> per-element state and roles
    var stateOf = new Dictionary<string, string>();
    var rolesOf = new Dictionary<string, List<string>>();
    string summary = "elements: " + elements.Count + Counts(elements) + (_errors.Count > 0 ? "\nunreadable branches: " + _errors.Count : "");
    int questions = -1;
    if (_sessionJson != null)
    {
      using (var jd = JsonDocument.Parse(_sessionJson))
      {
        var root = jd.RootElement;
        if (root.TryGetProperty("elements", out var els))
          foreach (var el in els.EnumerateArray())
          {
            var nid = el.GetProperty("nativeId").GetString();
            stateOf[nid] = el.GetProperty("state").GetString();
            rolesOf[nid] = el.GetProperty("roles").EnumerateArray().Select(r => r.GetProperty("label").GetString()).ToList();
          }
        if (root.TryGetProperty("summary", out var s))
        {
          questions = s.TryGetProperty("openQuestions", out var oq) ? oq.GetInt32() : -1;
          summary += "\nsession " + _sessionId + ": " + string.Join(", ",
            new[] { "confirmed", "auto", "suggested", "ambiguous", "unmapped" }
              .Where(n => s.TryGetProperty(n, out _)).Select(n => n + " " + s.GetProperty(n).GetInt32())) +
            ", open questions " + questions;
        }
      }
    }

    // ---- partition by class (apply result), original order kept
    var appliedRoles = new Dictionary<string, List<string>>();
    if (_applyJson != null)
    {
      using (var jd = JsonDocument.Parse(_applyJson))
        if (jd.RootElement.TryGetProperty("elements", out var els))
          foreach (var el in els.EnumerateArray())
            appliedRoles[el.GetProperty("nativeId").GetString()] =
              el.GetProperty("roles").EnumerateArray().Select(r => LocalName(r.GetString())).ToList();
    }
    var classOrder = new List<string>();
    if (Classes != null) classOrder.AddRange(Classes.Where(c => !string.IsNullOrWhiteSpace(c)).Select(c => c.Trim()));
    foreach (var c in appliedRoles.Values.SelectMany(r => r).Distinct().OrderBy(c => c, StringComparer.Ordinal))
      if (!classOrder.Contains(c)) classOrder.Add(c);
    var byClass = new DataTree<object>();
    for (int k = 0; k < classOrder.Count; k++)
    {
      var path = new GH_Path(k);
      byClass.EnsurePath(path);
      foreach (var e in elements)
      {
        List<string> roles;
        if (appliedRoles.TryGetValue(e.NativeId, out roles) && roles.Contains(classOrder[k])) byClass.Add(e.Preview, path);
      }
    }
    var classObjects = classOrder.Select(c => MatchClass(OntoClasses, c)).ToList();

    // ---- outputs
    SessionIdOut = _sessionId;
    Summary = summary;
    Questions = questions;
    Geometry = elements.Select(e => e.Preview).ToList();
    State = elements.Select(e => stateOf.TryGetValue(e.NativeId, out var st) ? st : "none").ToList();
    Colour = elements.Select(e => stateOf.TryGetValue(e.NativeId, out var st) && Palette.ContainsKey(st) ? Palette[st] : Palette["unmapped"]).ToList();
    Roles = elements.Select(e => rolesOf.TryGetValue(e.NativeId, out var rs) ? string.Join("+", rs) : "").ToList();
    NativeId = elements.Select(e => e.NativeId).ToList();
    ByClass = byClass;
    ClassNames = classOrder;
    ClassObjects = classObjects;
    Log = _lastLog + (_errors.Count > 0 ? "\n" + string.Join("\n", _errors.Take(20)) : "");
  }

  // ---------------------------------------------------------------- element model

  double _tol, _k;
  readonly List<string> _errors = new List<string>();

  class Element
  {
    public string NativeId, Source, Kind;
    public GeometryBase Preview;
    public readonly Dictionary<string, object> Geometry = new Dictionary<string, object>();
    public readonly Dictionary<string, object> Properties = new Dictionary<string, object>();
  }

  static string Counts(List<Element> elements)
  {
    var groups = elements.GroupBy(e => e.Source).Select(g => g.Key + " " + g.Count());
    return " (" + string.Join(", ", groups) + ")";
  }

  void ReadStream(DataTree<object> tree, string stream, string source, string key, List<double> levels, List<Element> outList)
  {
    if (tree == null) return;
    foreach (var path in tree.Paths)
    {
      var items = tree.Branch(path).Select(Unwrap).Where(o => o != null).ToList();
      if (items.Count == 0) continue;
      var e = new Element { NativeId = "gh:" + key + ":" + stream + ":" + path + ":0", Source = source };
      try { Describe(items, levels, e); }
      catch (Exception ex) { _errors.Add(stream + path + ": " + ex.Message); continue; }
      if (e.Preview == null) { _errors.Add(stream + path + ": unsupported geometry"); continue; }
      outList.Add(e);
    }
  }

  void ReadFacade(DataTree<object> tree, string key, List<Element> outList)
  {
    var bb = BoundingBox.Empty;
    foreach (var o in Flatten(tree))
    {
      var g = o as GeometryBase;
      if (g != null) bb.Union(g.GetBoundingBox(true));
    }
    if (!bb.IsValid) return;
    var e = new Element { NativeId = "gh:" + key + ":F:{0}:0", Source = "F", Kind = "box" };
    e.Preview = new Box(bb).ToBrep();
    e.Geometry["kind"] = "box";
    e.Geometry["zMinM"] = R(bb.Min.Z * _k);
    e.Geometry["zMaxM"] = R(bb.Max.Z * _k);
    e.Geometry["heightM"] = R((bb.Max.Z - bb.Min.Z) * _k);
    e.Properties["hasTotalHeightM"] = R((bb.Max.Z - bb.Min.Z) * _k);
    outList.Add(e);
  }

  void Describe(List<object> items, List<double> levels, Element e)
  {
    var curves = items.Select(AsCurve).Where(c => c != null).ToList();
    if (curves.Count == items.Count)
    {
      e.Kind = "curve";
      var pieces = curves.Count == 1 ? curves.ToArray() : Curve.JoinCurves(curves, Math.Max(_tol * 10, 0.001 / _k));
      if (pieces == null || pieces.Length == 0) throw new Exception("curves do not join");
      int gaps = pieces.Count(c => !c.IsClosed);
      var v = new List<Point3d>();
      foreach (var piece in pieces)
        foreach (var p in CurveVertices(piece))
          if (!v.Any(q => q.DistanceTo(p) <= _tol)) v.Add(p);
      e.Preview = pieces.Length == 1 ? (GeometryBase)pieces[0] : new PolylineCurve(new Polyline(v.Concat(new[] { v[0] })));
      e.Geometry["kind"] = "curve";
      e.Geometry["vertexCount"] = v.Count;
      e.Geometry["gapCount"] = gaps;
      e.Geometry["closed"] = gaps == 0;
      e.Geometry["zMinM"] = R(v.Min(p => p.Z) * _k);
      e.Geometry["zMaxM"] = R(v.Max(p => p.Z) * _k);
      e.Properties["hasVertexCount"] = v.Count;
      e.Properties["hasGapCount"] = gaps;
      if (levels.Count > 0)
        e.Properties["hasLevelOffsetM"] = R(v.Max(p => levels.Min(z => Math.Abs(p.Z - z))) * _k);
      return;
    }
    Brep brep = null;
    var breps = items.Select(AsBrep).Where(b => b != null).ToList();
    if (breps.Count == items.Count)
    {
      brep = breps.Count == 1 ? breps[0] : (Brep.JoinBreps(breps, _tol) ?? new Brep[0]).FirstOrDefault();
      if (brep == null) throw new Exception("surfaces do not join into one brep");
    }
    List<Point3d> corners = null;
    if (brep != null)
    {
      var loop = LargestFaceLoop(brep);
      if (loop == null) throw new Exception("brep without faces");
      corners = CurveVertices(loop);
      e.Preview = brep;
      var amp = AreaMassProperties.Compute(brep);
      if (amp != null) e.Geometry["areaM2"] = R(amp.Area * _k * _k);
    }
    else if (items.Count == 1 && items[0] is Mesh)
    {
      var naked = ((Mesh)items[0]).GetNakedEdges();
      if (naked == null || naked.Length == 0) throw new Exception("mesh without naked edges");
      corners = Clean(naked.OrderByDescending(p => p.Length).First());
      e.Preview = (Mesh)items[0];
    }
    if (corners == null) throw new Exception("unsupported item types");
    e.Kind = brep != null ? "surface" : "mesh";
    e.Geometry["kind"] = e.Kind;
    e.Geometry["vertexCount"] = corners.Count;
    e.Geometry["closed"] = true;
    e.Geometry["zMinM"] = R(corners.Min(p => p.Z) * _k);
    e.Geometry["zMaxM"] = R(corners.Max(p => p.Z) * _k);
    e.Properties["hasVertexCount"] = corners.Count;
    double vert, hor;
    EdgeStats(corners, out vert, out hor);
    double planarity = Planarity(corners) * _k;
    if (IsFinite(planarity)) { e.Geometry["planarityDeviationM"] = R(planarity); e.Properties["hasPlanarityDeviationM"] = R(planarity); }
    if (IsFinite(hor)) { e.Geometry["widthM"] = R(hor * _k); e.Properties["hasWidthM"] = R(hor * _k); }
    if (IsFinite(vert)) e.Geometry["heightM"] = R(vert * _k);
    if (IsFinite(vert) && IsFinite(hor) && hor > 0) e.Properties["hasAspectRatio"] = R(vert / hor);
  }

  // ---------------------------------------------------------------- JSON and HTTP

  static string SerializeDescriptors(IEnumerable<Element> elements, bool indented)
  {
    var list = elements.Select(e => new Dictionary<string, object>
    {
      { "nativeId", e.NativeId },
      { "platform", "grasshopper" },
      { "source", e.Source },
      { "geometry", e.Geometry },
      { "properties", e.Properties },
    }).ToList();
    return JsonSerializer.Serialize(list, new JsonSerializerOptions { WriteIndented = indented });
  }

  static string Send(HttpMethod method, string url, string body, string token, StringBuilder log)
  {
    using (var req = new HttpRequestMessage(method, url))
    {
      if (!string.IsNullOrWhiteSpace(token)) req.Headers.TryAddWithoutValidation("Authorization", "Bearer " + token.Trim());
      if (body != null) req.Content = new StringContent(body, Encoding.UTF8, "application/json");
      using (var resp = Http.SendAsync(req).GetAwaiter().GetResult())
      {
        var text = resp.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        var shortUrl = url.Split('?')[0];
        if (!resp.IsSuccessStatusCode)
        {
          log.AppendLine(method + " " + shortUrl + " -> " + (int)resp.StatusCode + " " + ErrorCode(text));
          return null;
        }
        log.AppendLine(method + " " + shortUrl + " -> " + (int)resp.StatusCode);
        return text;
      }
    }
  }

  static string ErrorCode(string text)
  {
    try
    {
      using (var jd = JsonDocument.Parse(text))
      {
        var root = jd.RootElement;
        if (root.TryGetProperty("detail", out var d))
        {
          if (d.ValueKind == JsonValueKind.Object && d.TryGetProperty("code", out var c)) return c.GetString();
          if (d.ValueKind == JsonValueKind.String) return d.GetString();
        }
        if (root.TryGetProperty("code", out var c2)) return c2.GetString();
      }
    }
    catch { }
    return "(no error code)";
  }

  static string ReadString(string json, string name)
  {
    using (var jd = JsonDocument.Parse(json))
      return jd.RootElement.TryGetProperty(name, out var v) ? v.GetString() : null;
  }

  static string LocalName(string iri)
  {
    if (string.IsNullOrEmpty(iri)) return iri;
    foreach (var sep in new[] { '#', '/', ':' })
    {
      int i = iri.LastIndexOf(sep);
      if (i >= 0) iri = iri.Substring(i + 1);
    }
    return iri;
  }

  // OntoClasses items are DG OntologyClass objects (properties Iri, Label); read by reflection
  // so the script does not reference the DG assembly.
  static object MatchClass(List<object> ontoClasses, string label)
  {
    if (ontoClasses == null) return null;
    foreach (var o in ontoClasses)
    {
      var c = Unwrap(o);
      if (c == null) continue;
      var t = c.GetType();
      var iri = t.GetProperty("Iri")?.GetValue(c) as string;
      var lab = t.GetProperty("Label")?.GetValue(c) as string;
      if (string.Equals(lab, label, StringComparison.Ordinal) || string.Equals(LocalName(iri), label, StringComparison.Ordinal)) return o;
    }
    return null;
  }

  // ---------------------------------------------------------------- geometry (from gh-measure-rules.cs)

  static IEnumerable<object> Flatten(DataTree<object> tree)
  {
    if (tree == null) yield break;
    foreach (var o in tree.AllData()) { var u = Unwrap(o); if (u != null) yield return u; }
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

  static double ToDouble(object o)
  {
    o = Unwrap(o);
    if (o == null) return double.NaN;
    try { return Convert.ToDouble(o, CultureInfo.InvariantCulture); } catch { return double.NaN; }
  }

  static bool IsFinite(double x) { return !double.IsNaN(x) && !double.IsInfinity(x); }

  static double R(double x) { return Math.Round(x, 6); }
}
