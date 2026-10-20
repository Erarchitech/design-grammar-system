#if GRASSHOPPER_SDK && NETFRAMEWORK
using System.Reflection;
using Grasshopper.Kernel;

namespace DG.Grasshopper;

/// <summary>
/// Phase 1303-15: on .NET Framework (Rhino.Inside.Revit in Revit 2024) a plug-in has no binding redirects, so the
/// package dependencies DG ships (Neo4j.Driver wants Microsoft.Bcl.AsyncInterfaces 6.0, System.Buffers 4.0.2,
/// System.Memory wants System.Runtime.CompilerServices.Unsafe 4.0.4.1, ...) fail to bind against the newer files in
/// the DG folder ("Connect failed"). This resolver answers such a failed bind with the assembly of the same simple
/// name from the DG folder, whatever version was asked for. It runs before any DG component loads.
/// </summary>
public sealed class NetFrameworkAssemblyResolver : GH_AssemblyPriority
{
    private static readonly string Folder = Path.GetDirectoryName(typeof(NetFrameworkAssemblyResolver).Assembly.Location) ?? string.Empty;
    private static int _registered;

    public override GH_LoadingInstruction PriorityLoad()
    {
        if (Interlocked.Exchange(ref _registered, 1) == 0)
        {
            AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        }

        return GH_LoadingInstruction.Proceed;
    }

    private static Assembly? Resolve(object? sender, ResolveEventArgs args)
    {
        var name = new AssemblyName(args.Name).Name;
        if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(Folder))
        {
            return null;
        }

        var loaded = AppDomain.CurrentDomain.GetAssemblies()
            .FirstOrDefault(a => string.Equals(a.GetName().Name, name, StringComparison.OrdinalIgnoreCase)
                && string.Equals(Path.GetDirectoryName(SafeLocation(a)), Folder, StringComparison.OrdinalIgnoreCase));
        if (loaded is not null)
        {
            return loaded;
        }

        var path = Path.Combine(Folder, name + ".dll");
        return File.Exists(path) ? Assembly.LoadFrom(path) : null;
    }

    private static string SafeLocation(Assembly assembly)
    {
        try
        {
            return assembly.IsDynamic ? string.Empty : assembly.Location;
        }
        catch (NotSupportedException)
        {
            return string.Empty;
        }
    }
}
#endif
