#if GRASSHOPPER_SDK
using System.Collections;
using Rhino;
using Rhino.Geometry;

namespace DG.Grasshopper.Validation;

internal static class ValidationGeometryPayloadSerializer
{
    public static ValidationGeometryPayload? Serialize(object? geometry)
    {
        if (geometry is null)
        {
            return null;
        }

        var payload = new ValidationGeometryPayload
        {
            Units = ResolveUnits(),
        };

        foreach (var item in SerializeItems(geometry))
        {
            payload.Items.Add(item);
        }

        return payload.Items.Count == 0 ? null : payload;
    }

    private static IEnumerable<ValidationGeometryItemPayload> SerializeItems(object geometry)
    {
        if (geometry is null)
        {
            yield break;
        }

        if (geometry is Mesh mesh)
        {
            yield return SerializeMesh(mesh);
            yield break;
        }

        if (geometry is Brep brep)
        {
            foreach (var brepMesh in Mesh.CreateFromBrep(brep, MeshingParameters.FastRenderMesh) ?? Array.Empty<Mesh>())
            {
                yield return SerializeMesh(brepMesh);
            }
            yield break;
        }

        if (geometry is Surface surface)
        {
            foreach (var brepMesh in Mesh.CreateFromBrep(surface.ToBrep(), MeshingParameters.FastRenderMesh) ?? Array.Empty<Mesh>())
            {
                yield return SerializeMesh(brepMesh);
            }
            yield break;
        }

        if (geometry is Extrusion extrusion)
        {
            var extrusionMesh = extrusion.GetMesh(MeshType.Render);
            if (extrusionMesh is not null)
            {
                yield return SerializeMesh(extrusionMesh);
            }
            yield break;
        }

        if (geometry is Polyline directPolyline && directPolyline.Count >= 2)
        {
            yield return SerializePolyline(directPolyline);
            yield break;
        }

        if (geometry is Curve curve)
        {
            if (curve.TryGetPolyline(out var polyline) && polyline.Count >= 2)
            {
                yield return SerializePolyline(polyline);
                yield break;
            }

            var divisionParameters = curve.DivideByCount(32, true) ?? Array.Empty<double>();
            if (divisionParameters.Length >= 2)
            {
                var approximated = new Polyline(divisionParameters.Select(curve.PointAt));
                yield return SerializePolyline(approximated);
            }
            yield break;
        }

        if (geometry is Line line)
        {
            yield return SerializeLine(line);
            yield break;
        }

        if (geometry is Point3d point3d)
        {
            yield return SerializePoint(point3d);
            yield break;
        }

        if (geometry is Rhino.Geometry.Point rhinoPoint)
        {
            yield return SerializePoint(rhinoPoint.Location);
            yield break;
        }

        if (geometry is IEnumerable enumerable && geometry is not string)
        {
            foreach (var item in enumerable)
            {
                foreach (var serialized in SerializeItems(item!))
                {
                    yield return serialized;
                }
            }

            yield break;
        }

        // Phase 1303-15 (live 2026-10-21): inside Rhino.Inside.Revit a Python 3 script sees a second RhinoCommon, so a
        // Brep it builds is not this assembly's Brep and every check above fails; the published boxes had no geometry.
        // Any foreign geometry with GetBoundingBox(bool) is published as its bounding box.
        if (TryForeignBoundingBox(geometry, out var box))
        {
            var boxMesh = Mesh.CreateFromBox(box, 1, 1, 1);
            if (boxMesh is not null)
            {
                yield return SerializeMesh(boxMesh);
            }
        }
    }

    private static bool TryForeignBoundingBox(object geometry, out BoundingBox box)
    {
        box = BoundingBox.Empty;
        try
        {
            var method = geometry.GetType().GetMethod("GetBoundingBox", new[] { typeof(bool) });
            var bb = method?.Invoke(geometry, new object[] { true });
            if (bb is null)
            {
                return false;
            }

            static Point3d Corner(object bb, string name)
            {
                var p = bb.GetType().GetProperty(name)!.GetValue(bb)!;
                double C(string axis) => Convert.ToDouble(p.GetType().GetProperty(axis)!.GetValue(p));
                return new Point3d(C("X"), C("Y"), C("Z"));
            }

            box = new BoundingBox(Corner(bb, "Min"), Corner(bb, "Max"));
            return box.IsValid;
        }
        catch (Exception)
        {
            return false;
        }
    }

    private static ValidationGeometryItemPayload SerializeMesh(Mesh mesh)
    {
        var duplicate = mesh.DuplicateMesh();
        duplicate.Normals.ComputeNormals();
        duplicate.Compact();

        var item = new ValidationGeometryItemPayload
        {
            Kind = "mesh",
        };

        foreach (var vertex in duplicate.Vertices)
        {
            item.Vertices.Add(vertex.X);
            item.Vertices.Add(vertex.Y);
            item.Vertices.Add(vertex.Z);
        }

        foreach (var face in duplicate.Faces)
        {
            if (face.IsTriangle)
            {
                item.Faces.Add(new List<int> { face.A, face.B, face.C });
            }
            else
            {
                item.Faces.Add(new List<int> { face.A, face.B, face.C, face.D });
            }
        }

        if (duplicate.VertexColors.Count == duplicate.Vertices.Count)
        {
            foreach (var color in duplicate.VertexColors)
            {
                item.Colors.Add(color.ToArgb());
            }
        }

        return item;
    }

    private static ValidationGeometryItemPayload SerializePolyline(Polyline polyline)
    {
        var item = new ValidationGeometryItemPayload
        {
            Kind = "polyline",
        };

        foreach (var point in polyline)
        {
            item.Values.Add(point.X);
            item.Values.Add(point.Y);
            item.Values.Add(point.Z);
        }

        return item;
    }

    private static ValidationGeometryItemPayload SerializeLine(Line line)
    {
        var item = new ValidationGeometryItemPayload
        {
            Kind = "line",
        };

        item.Values.Add(line.FromX);
        item.Values.Add(line.FromY);
        item.Values.Add(line.FromZ);
        item.Values.Add(line.ToX);
        item.Values.Add(line.ToY);
        item.Values.Add(line.ToZ);
        return item;
    }

    private static ValidationGeometryItemPayload SerializePoint(Point3d point)
    {
        var item = new ValidationGeometryItemPayload
        {
            Kind = "point",
        };

        item.Values.Add(point.X);
        item.Values.Add(point.Y);
        item.Values.Add(point.Z);
        return item;
    }

    private static string ResolveUnits()
    {
        var unitSystem = RhinoDoc.ActiveDoc?.ModelUnitSystem ?? UnitSystem.Meters;
        return unitSystem switch
        {
            UnitSystem.Meters => "m",
            UnitSystem.Centimeters => "cm",
            UnitSystem.Millimeters => "mm",
            UnitSystem.Feet => "ft",
            UnitSystem.Inches => "in",
            UnitSystem.Kilometers => "km",
            UnitSystem.Yards => "yd",
            UnitSystem.Miles => "mi",
            _ => unitSystem.ToString().ToLowerInvariant(),
        };
    }
}
#else
namespace DG.Grasshopper.Validation;

internal static class ValidationGeometryPayloadSerializer
{
}
#endif
