#if GRASSHOPPER_SDK
using System.Drawing;
using System.Reflection;

namespace DG.Grasshopper;

internal static class DgIcons
{
    public static Bitmap Connector24 { get; } = Load("Connector24.png");

    public static Bitmap Metagraph24 { get; } = Load("Metagraph24.png");

    public static Bitmap RuleDeconstruct24 { get; } = Load("RuleDeconstruct24.png");
    public static Bitmap Validator24 { get; } = Load("Validator24.png");

    public static Bitmap ParameterState24 { get; } = Load("ParameterState24.png");

    public static Bitmap ObjectState24 { get; } = Load("ObjectState24.png");

    public static Bitmap PropertyState24 { get; } = Load("PropertyState24.png");

    public static Bitmap DesignStateComposition24 { get; } = Load("DesignStateComposition24.png");

    public static Bitmap Reinstate24 { get; } = Load("Reinstate24.png");

    public static Bitmap DesignStateDeconstruct24 { get; } = Load("DesignStateDeconstruct24.png");

    public static Bitmap GraphDeconstruct24 { get; } = Load("GraphDeconstruct24.png");

    public static Bitmap ObjectDeconstruct24 { get; } = Load("ObjectDeconstruct24.png");

    public static Bitmap OntoGraph24 { get; } = Load("OntoGraph24.png");

    public static Bitmap ParameterReinstate24 { get; } = Load("ParameterReinstate24.png");

    public static Bitmap ValidationGraph24 { get; } = Load("ValidationGraph24.png");

    public static Bitmap Label24 { get; } = Load("Label24.png");

    // CanvasListener24.png is a Phase-19-convention placeholder (copy of the spare
    // DesignState24.png resource) so DG CANVAS LISTENER does not render the pink-X
    // missing-icon fallback (WR-07); replace with bespoke artwork when available.
    public static Bitmap CanvasListener24 { get; } = Load("CanvasListener24.png");

    // ObjectMarker24.png is a Phase-34 placeholder (copy of the spare OntoGraph24.png
    // resource) so DG OBJECT MARKER does not render the pink-X missing-icon fallback
    // (WR-07 precedent); replace with bespoke artwork when available.
    public static Bitmap ObjectMarker24 { get; } = Load("ObjectMarker24.png");

    private static Bitmap Load(string fileName)
    {
        var assembly = Assembly.GetExecutingAssembly();
        var resourceName = $"{typeof(DgIcons).Namespace}.Properties.{fileName}";

        using var stream = assembly.GetManifestResourceStream(resourceName);
        if (stream is null)
        {
            var fallback = new Bitmap(24, 24);
            using var g = Graphics.FromImage(fallback);
            g.Clear(Color.LightPink);
            g.DrawLine(Pens.Red, 0, 0, 24, 24);
            g.DrawLine(Pens.Red, 24, 0, 0, 24);
            return fallback;
        }

        using var source = new Bitmap(stream);
        return new Bitmap(source);
    }
}
#else
namespace DG.Grasshopper;

internal static class DgIcons
{
}
#endif
