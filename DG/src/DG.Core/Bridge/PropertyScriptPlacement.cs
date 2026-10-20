using System.Text.Json;

namespace DG.Core.Bridge;

/// <summary>
/// Phase 1303-15 (DGOPN-02): the parsed and validated payload of the <c>place_property_script</c>
/// bridge command. data-service generates the scripts and the placement plan
/// (<c>property_scripts.py</c>); CanvasListenerComponent executes it. Parsing and validation live
/// here, free of Grasshopper types, so they are unit-tested.
/// </summary>
public static class PropertyScriptPlacement
{
    /// <summary>DG component types a plan may create or reuse, by display name.</summary>
    public static IReadOnlyDictionary<string, Guid> DgComponentTypes { get; } = new Dictionary<string, Guid>(StringComparer.Ordinal)
    {
        ["CONNECTOR"] = new("EF2E6F2A-3450-4907-94CB-31B1240AB848"),
        ["METAGRAPH"] = new("6ED440FB-EF12-49D1-8969-74A2B0E72360"),
        ["OBJECT STATE"] = new("F9A1D8B2-C4E6-4F7A-9B5D-3E8C2A1F6D0B"),
        ["PROPERTY STATE"] = new("C5D2E7F8-1A3B-4C6D-9E0F-8B7A2C4D6E1F"),
        ["DESIGN STATE"] = new("E7F2D8B1-6A3C-4F9E-8B0D-5C1A7E3F2D4B"),
        ["RULE BY ID"] = new("6C1F3B8E-2A47-4D95-B0E6-91D7C4A35F28"),
        ["VALIDATOR"] = new("C202D04A-9CC2-4CD1-9F47-C77D4093D447"),
    };

    /// <summary>The Rhino 8 "Python 3 Script" component (RhinoCodePluginGH.Components.Python3Component).</summary>
    public static Guid Python3ScriptComponent { get; } = new("719467e6-7cf5-4848-99b0-c5dd57e5442c");

    public static readonly HashSet<string> Kinds = new HashSet<string>(StringComparer.Ordinal) { "dg", "script", "toggle", "panel" };

    public static readonly HashSet<string> Accesses = new HashSet<string>(StringComparer.Ordinal) { "item", "list", "tree" };

    public static PropertyScriptPlan Parse(JsonElement parameters)
    {
        if (parameters.ValueKind != JsonValueKind.Object)
        {
            throw new PropertyScriptPlanException("parameters must be an object");
        }

        var project = Str(parameters, "project");
        var scripts = new Dictionary<string, ScriptSpec>(StringComparer.Ordinal);
        foreach (var name in new[] { "calculator", "highlighter" })
        {
            if (parameters.TryGetProperty(name, out var s) && s.ValueKind == JsonValueKind.Object)
            {
                scripts[name] = ParseScript(s);
            }
        }

        if (!parameters.TryGetProperty("placement", out var placement) || placement.ValueKind != JsonValueKind.Object)
        {
            throw new PropertyScriptPlanException("placement is missing");
        }

        var components = new List<PlanComponent>();
        if (placement.TryGetProperty("components", out var comps) && comps.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in comps.EnumerateArray())
            {
                components.Add(new PlanComponent(
                    Str(c, "key"),
                    Str(c, "kind"),
                    Str(c, "type"),
                    Str(c, "script"),
                    Str(c, "nickname"),
                    Str(c, "text"),
                    Bool(c, "value"),
                    Bool(c, "reuse"),
                    Bool(c, "required"),
                    Num(c, "x"),
                    Num(c, "y")));
            }
        }

        var wires = new List<PlanWire>();
        if (placement.TryGetProperty("wires", out var ws) && ws.ValueKind == JsonValueKind.Array)
        {
            foreach (var w in ws.EnumerateArray())
            {
                if (w.ValueKind != JsonValueKind.Array || w.GetArrayLength() != 2)
                {
                    throw new PropertyScriptPlanException("each wire is [\"key.port\", \"key.port\"]");
                }

                wires.Add(new PlanWire(PlanEnd.Parse(w[0].GetString() ?? string.Empty), PlanEnd.Parse(w[1].GetString() ?? string.Empty)));
            }
        }

        var plan = new PropertyScriptPlan(project, Str(placement, "group"), scripts, components, wires);
        Validate(plan);
        return plan;
    }

    public static void Validate(PropertyScriptPlan plan)
    {
        if (plan.Components.Count == 0)
        {
            throw new PropertyScriptPlanException("placement has no components");
        }

        var keys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in plan.Components)
        {
            if (string.IsNullOrWhiteSpace(c.Key) || !keys.Add(c.Key))
            {
                throw new PropertyScriptPlanException($"component key '{c.Key}' is empty or duplicated");
            }

            if (!Kinds.Contains(c.Kind))
            {
                throw new PropertyScriptPlanException($"component '{c.Key}' has unknown kind '{c.Kind}'");
            }

            if (c.Kind == "dg" && !DgComponentTypes.ContainsKey(c.Type))
            {
                throw new PropertyScriptPlanException($"component '{c.Key}' has unknown DG type '{c.Type}'");
            }

            if (c.Kind == "script" && !plan.Scripts.ContainsKey(c.Script))
            {
                throw new PropertyScriptPlanException($"component '{c.Key}' references missing script '{c.Script}'");
            }

            if (c.Reuse && c.Kind != "dg")
            {
                throw new PropertyScriptPlanException($"component '{c.Key}': only DG components can be reused");
            }
        }

        foreach (var w in plan.Wires)
        {
            foreach (var end in new[] { w.From, w.To })
            {
                if (!keys.Contains(end.Key))
                {
                    throw new PropertyScriptPlanException($"wire end '{end}' names an unknown component");
                }

                var comp = plan.Components.First(c => c.Key == end.Key);
                var isParamObject = comp.Kind is "toggle" or "panel";
                if (isParamObject != string.IsNullOrEmpty(end.Port))
                {
                    throw new PropertyScriptPlanException($"wire end '{end}': toggles and panels take no port, components need one");
                }

                if (comp.Kind == "script")
                {
                    var script = plan.Scripts[comp.Script];
                    var ports = script.Inputs.Select(i => i.Name).Concat(script.Outputs);
                    if (!ports.Contains(end.Port, StringComparer.Ordinal))
                    {
                        throw new PropertyScriptPlanException($"wire end '{end}': script '{comp.Script}' has no port '{end.Port}'");
                    }
                }
            }

            var target = plan.Components.First(c => c.Key == w.To.Key);
            if (target.Kind is "toggle" or "panel")
            {
                throw new PropertyScriptPlanException($"wire '{w.From} -> {w.To}': a toggle or panel cannot be a wire target");
            }
        }
    }

    private static ScriptSpec ParseScript(JsonElement s)
    {
        var language = Str(s, "language");
        if (language != "python3")
        {
            throw new PropertyScriptPlanException($"script language '{language}' is not supported (python3 only)");
        }

        var source = Str(s, "source");
        if (string.IsNullOrWhiteSpace(source))
        {
            throw new PropertyScriptPlanException("script source is empty");
        }

        var inputs = new List<ScriptPort>();
        if (s.TryGetProperty("inputs", out var ins) && ins.ValueKind == JsonValueKind.Array)
        {
            foreach (var i in ins.EnumerateArray())
            {
                var access = Str(i, "access");
                if (!Accesses.Contains(access))
                {
                    throw new PropertyScriptPlanException($"script input access '{access}' is not item/list/tree");
                }

                inputs.Add(new ScriptPort(Str(i, "name"), access));
            }
        }

        var outputs = new List<string>();
        if (s.TryGetProperty("outputs", out var outs) && outs.ValueKind == JsonValueKind.Array)
        {
            outputs.AddRange(outs.EnumerateArray().Select(o => o.GetString() ?? string.Empty));
        }

        foreach (var name in inputs.Select(i => i.Name).Concat(outputs))
        {
            if (!IsIdentifier(name))
            {
                throw new PropertyScriptPlanException($"script port '{name}' is not a valid identifier");
            }
        }

        return new ScriptSpec(Str(s, "nickname"), source, inputs, outputs, Str(s, "sha256"));
    }

    internal static bool IsIdentifier(string name) =>
        !string.IsNullOrEmpty(name)
        && (char.IsLetter(name[0]) || name[0] == '_')
        && name.All(ch => char.IsLetterOrDigit(ch) || ch == '_');

    private static string Str(JsonElement e, string key) =>
        e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() ?? string.Empty : string.Empty;

    private static bool Bool(JsonElement e, string key) =>
        e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.True;

    private static float Num(JsonElement e, string key) =>
        e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number ? (float)v.GetDouble() : 0f;
}

public sealed record PropertyScriptPlan(
    string Project,
    string Group,
    IReadOnlyDictionary<string, ScriptSpec> Scripts,
    IReadOnlyList<PlanComponent> Components,
    IReadOnlyList<PlanWire> Wires);

public sealed record ScriptSpec(string NickName, string Source, IReadOnlyList<ScriptPort> Inputs, IReadOnlyList<string> Outputs, string Sha256);

public sealed record ScriptPort(string Name, string Access);

public sealed record PlanComponent(
    string Key,
    string Kind,
    string Type,
    string Script,
    string NickName,
    string Text,
    bool Value,
    bool Reuse,
    bool Required,
    float X,
    float Y);

public sealed record PlanWire(PlanEnd From, PlanEnd To);

public sealed record PlanEnd(string Key, string Port)
{
    public static PlanEnd Parse(string text)
    {
        var dot = text.IndexOf('.');
        if (dot <= 0)
        {
            throw new PropertyScriptPlanException($"wire end '{text}' is not 'key.port'");
        }

        return new PlanEnd(text[..dot], text[(dot + 1)..]);
    }

    public override string ToString() => $"{Key}.{Port}";
}

public sealed class PropertyScriptPlanException : Exception
{
    public PropertyScriptPlanException(string message)
        : base(message)
    {
    }
}
