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
