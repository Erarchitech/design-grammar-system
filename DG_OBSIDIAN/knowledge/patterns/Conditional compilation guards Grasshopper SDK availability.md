---
tags: [pattern, csharp, conditional-compilation, grasshopper]
date: 2026-04-05
---

# Conditional Compilation Guards Grasshopper SDK Availability

## Pattern

`DG.Grasshopper` uses `#if GRASSHOPPER_SDK` preprocessor directives to compile as either a full Grasshopper plugin (when Rhino 8 SDK DLLs are present) or an empty placeholder assembly.

## Implementation

```csharp
#if GRASSHOPPER_SDK
public sealed class ConnectorComponent : GH_Component {
    // Full implementation...
}
#else
public sealed class ConnectorComponent { }
#endif
```

## SDK Detection (`.csproj`)

```xml
<PropertyGroup>
  <RhinoInstallDir>C:\Program Files\Rhino 8</RhinoInstallDir>
</PropertyGroup>

<ItemGroup Condition="Exists('$(RhinoInstallDir)\System\RhinoCommon.dll')">
  <Reference Include="RhinoCommon" ... />
  <Reference Include="Grasshopper" ... />
  <DefineConstants>$(DefineConstants);GRASSHOPPER_SDK</DefineConstants>
</ItemGroup>
```

## Why This Pattern

- **CI/CD compatibility** — builds pass on machines without Rhino installed
- **Core library independence** — `DG.Core` never depends on Grasshopper; tests run without SDK
- **Override support** — `dotnet build -p:RhinoInstallDir="D:\Apps\Rhino 8"` for custom installs

## Related

- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[Grasshopper async component with ScheduleSolution polling]]
- [[Technology stack spans C-Sharp Grasshopper and Python FastAPI and React SPA]]
