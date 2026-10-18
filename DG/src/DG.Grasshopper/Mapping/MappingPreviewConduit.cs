#if GRASSHOPPER_SDK
using System.Drawing;
using Rhino.Display;
using Rhino.Geometry;

namespace DG.Grasshopper.Mapping;

/// <summary>
/// Draws every mapped element in the colour of its mapping state, so the canvas needs no
/// Custom Preview wiring (Phase 1303). Colours as in the Web UI.
/// </summary>
internal sealed class MappingPreviewConduit : DisplayConduit
{
    public static readonly IReadOnlyDictionary<string, Color> Palette = new Dictionary<string, Color>(StringComparer.Ordinal)
    {
        ["confirmed"] = ColorTranslator.FromHtml("#2E7D32"),
        ["auto"] = ColorTranslator.FromHtml("#1565C0"),
        ["suggested"] = ColorTranslator.FromHtml("#F9A825"),
        ["ambiguous"] = ColorTranslator.FromHtml("#E65100"),
        ["unmapped"] = ColorTranslator.FromHtml("#9E9E9E"),
    };

    private volatile IReadOnlyList<(GeometryBase Geometry, Color Colour)> _items = Array.Empty<(GeometryBase, Color)>();
    private BoundingBox _box = BoundingBox.Empty;

    public void Update(IReadOnlyList<(GeometryBase Geometry, Color Colour)> items)
    {
        var box = BoundingBox.Empty;
        foreach (var (g, _) in items)
        {
            box.Union(g.GetBoundingBox(false));
        }

        _box = box;
        _items = items;
    }

    public static Color ColourOf(string? state) =>
        state is not null && Palette.TryGetValue(state, out var c) ? c : Palette["unmapped"];

    protected override void CalculateBoundingBox(CalculateBoundingBoxEventArgs e)
    {
        if (_box.IsValid)
        {
            e.IncludeBoundingBox(_box);
        }
    }

    protected override void PostDrawObjects(DrawEventArgs e)
    {
        foreach (var (g, colour) in _items)
        {
            switch (g)
            {
                case Curve c:
                    e.Display.DrawCurve(c, colour, 4);
                    break;
                case Brep b:
                    e.Display.DrawBrepShaded(b, new DisplayMaterial(colour, 0.35));
                    e.Display.DrawBrepWires(b, colour, 0);
                    break;
                case Mesh m:
                    e.Display.DrawMeshShaded(m, new DisplayMaterial(colour, 0.35));
                    break;
            }
        }
    }
}
#endif
