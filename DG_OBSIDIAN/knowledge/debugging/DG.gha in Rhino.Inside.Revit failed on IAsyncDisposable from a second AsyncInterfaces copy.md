---
tags: [debugging, phase-1303, rhino-inside, grasshopper, dotnet]
date: 2026-10-21
status: fixed (commits dccd6c9, 99e2127, a870b75)
---

# DG.gha in Rhino.Inside.Revit failed on IAsyncDisposable from a second AsyncInterfaces copy

**Symptom.** In Rhino.Inside.Revit (Revit 2024, .NET Framework 4.8):
- The DG components did not appear at first, because DG.gha was net7-only.
- After the net48 build, CONNECTOR showed "Connect failed": first binding errors, then «Точка входа не найдена» (EntryPointNotFoundException).

**Cause.** Several plug-ins loaded in Revit ship their own `Microsoft.Bcl.AsyncInterfaces`: Carbon Insights 6.0, Rhino 7.0, Speckle 5.0 and DG 8.0. The Neo4j driver's `IAsyncDisposable.DisposeAsync`, reached through `await using`, resolved against an interface from another copy, and the call had no entry point.

**Fixes.**
1. DG.gha is multi-targeted `net7.0-windows;net48`, with polyfills (PolySharp, System.Text.Json, Microsoft.Bcl.HashCode, System.Net.Http.Json).
2. `NetFrameworkAssemblyResolver` (GH_AssemblyPriority) runs first in `AppDomain.AssemblyResolve`. It reuses an already loaded copy, or serves DG's own.
3. `await using` → synchronous `using` on the Neo4j driver objects. This removed the last `IAsyncDisposable` call; CONNECTOR shows Connected.

**Notes.**
- Install DG.gha only while Revit/Rhino are closed.
- Choose Rhino 8, not 7, when Rhino.Inside starts.
- The status output of the check (`assemblyResolver`) lists which copies were served.

Related: [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR|session]], `DG/src/DG.Grasshopper/NetFrameworkAssemblyResolver.cs`.
