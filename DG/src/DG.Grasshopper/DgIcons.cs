#if GRASSHOPPER_SDK
using System.Drawing;
using System.Reflection;

namespace DG.Grasshopper;

internal static class DgIcons
{
    public static Bitmap Connector24 { get; } = Load("Connector24.png");

    public static Bitmap Metagraph24 { get; } = Load("Metagraph24.png");

    public static Bitmap RuleDeconstruct24 { get; } = Load("RuleDeconstruct24.png");

    public static Bitmap Classificator24 { get; } = Load("Classificator24.png");

    public static Bitmap Validator24 { get; } = Load("Validator24.png");

    public static Bitmap ParameterState24 { get; } = Load("ParameterState24.png");

    public static Bitmap ObjectState24 { get; } = Load("ObjectState24.png");

    public static Bitmap PropertyState24 { get; } = Load("PropertyState24.png");

    public static Bitmap Reinstate24 { get; } = Load("Reinstate24.png");

    public static Bitmap ValidationRuns24 { get; } = Load("ValidationRuns24.png");

    private static Bitmap Load(string fileName)
    {
        var assembly = Assembly.GetExecutingAssembly();
        var resourceName = $"{typeof(DgIcons).Namespace}.Properties.{fileName}";

        using var stream = assembly.GetManifestResourceStream(resourceName);
        if (stream is null)
        {
            return new Bitmap(24, 24);
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
