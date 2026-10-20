#if GRASSHOPPER_SDK && NETFRAMEWORK
using System.Reflection;
using Grasshopper.Kernel;

namespace DG.Grasshopper;

/// <summary>
/// Phase 1303-15: on .NET Framework (Rhino.Inside.Revit in Revit 2024) a plug-in has no binding redirects, so the
/// package dependencies DG ships (Neo4j.Driver wants Microsoft.Bcl.AsyncInterfaces 6.0, System.Buffers 4.0.2,
/// System.Memory wants System.Runtime.CompilerServices.Unsafe 4.0.4.1, ...) fail to bind against the files in the DG
/// folder and the AppDomain raises AssemblyResolve.
///
/// Rhino.Inside registers its own resolver earlier and answers with the copies in <c>Rhino 8\System</c>. Mixing
/// those with DG's copies made Neo4j.Driver fail with "Entry point was not found" (CONNECTOR "Connect failed",
/// live 2026-10-20; reproduced in a .NET Framework console with a host resolver registered first). So DG's resolver
/// is moved to the FRONT of the AppDomain's handler list, and for every assembly the DG folder ships it answers with
/// that copy (the one already loaded from the folder, or loads it). Other names fall through to the host resolvers.
/// </summary>
public sealed class NetFrameworkAssemblyResolver : GH_AssemblyPriority
{
    private static readonly string Folder = FindFolder();

    /// <summary>The folder holding DG.gha and its dependencies. Grasshopper may load a .gha from bytes, leaving
    /// Assembly.Location empty, so the Grasshopper library folders are searched for DG.gha as a fallback.</summary>
    private static string FindFolder()
    {
        try
        {
            var location = typeof(NetFrameworkAssemblyResolver).Assembly.Location;
            if (!string.IsNullOrEmpty(location))
            {
                return Path.GetDirectoryName(location) ?? string.Empty;
            }
        }
        catch (NotSupportedException)
        {
        }

        foreach (var info in global::Grasshopper.Folders.AssemblyFolders)
        {
            var root = info.Folder;
            if (string.IsNullOrEmpty(root) || !Directory.Exists(root))
            {
                continue;
            }

            var hit = Directory.EnumerateFiles(root, "DG.gha", SearchOption.AllDirectories).FirstOrDefault();
            if (hit is not null)
            {
                return Path.GetDirectoryName(hit) ?? string.Empty;
            }
        }

        return string.Empty;
    }
    private static readonly object Gate = new();
    private static int _registered;

    public override GH_LoadingInstruction PriorityLoad()
    {
        if (Interlocked.Exchange(ref _registered, 1) == 0)
        {
            RegisterFirst();
        }

        return GH_LoadingInstruction.Proceed;
    }

    /// <summary>Puts <see cref="Resolve"/> before every handler already registered (AppDomain raises them in
    /// order and uses the first non-null answer). Falls back to a plain subscription if the runtime field differs.</summary>
    private static void RegisterFirst()
    {
        var field = typeof(AppDomain).GetField("_AssemblyResolve", BindingFlags.Instance | BindingFlags.NonPublic);
        if (field is null || field.FieldType != typeof(ResolveEventHandler))
        {
            AppDomain.CurrentDomain.AssemblyResolve += Resolve;
            return;
        }

        lock (Gate)
        {
            var current = field.GetValue(AppDomain.CurrentDomain) as ResolveEventHandler;
            field.SetValue(AppDomain.CurrentDomain, (ResolveEventHandler)Delegate.Combine(new ResolveEventHandler(Resolve), current));
        }
    }

    private static Assembly? Resolve(object? sender, ResolveEventArgs args)
    {
        var name = new AssemblyName(args.Name).Name;
        if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(Folder))
        {
            return null;
        }

        var path = Path.Combine(Folder, name + ".dll");
        if (!File.Exists(path))
        {
            return null; // not a DG dependency: the host resolvers decide
        }

        var full = Path.GetFullPath(path);
        var loaded = AppDomain.CurrentDomain.GetAssemblies()
            .FirstOrDefault(a => string.Equals(a.GetName().Name, name, StringComparison.OrdinalIgnoreCase)
                && string.Equals(SafeLocation(a), full, StringComparison.OrdinalIgnoreCase));
        return loaded ?? Assembly.LoadFrom(full);
    }

    private static string SafeLocation(Assembly assembly)
    {
        try
        {
            return assembly.IsDynamic || string.IsNullOrEmpty(assembly.Location) ? string.Empty : Path.GetFullPath(assembly.Location);
        }
        catch (NotSupportedException)
        {
            return string.Empty;
        }
    }
}
#endif
