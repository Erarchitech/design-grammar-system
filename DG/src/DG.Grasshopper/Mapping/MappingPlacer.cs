#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Mapping;
using DG.Grasshopper.Components;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;

namespace DG.Grasshopper.Mapping;

/// <summary>
/// Places and wires the DG components once the mapping is agreed (Phase 1303, 1303-CONTEXT
/// D-38): GRAPH DECONSTRUCT → METAGRAPH; one OBJECT STATE per class (Object = "class:&lt;IRI&gt;",
/// Geometry ← the element streams); one RULE BY ID + PROPERTY STATE per rule binding
/// (DataProperty = property IRI, PropValue ← the calculation output, ObjState ← the class's
/// OBJECT STATE); one PARAMETER STATE with an input per DG parameter slider; DESIGN STATE; and
/// VALIDATOR (SendValid = false, Token ← CONNECTOR.Session). Classes and rules are bound by
/// identity, never by a list index. Everything is added in one undo record and one group.
/// </summary>
internal static class MappingPlacer
{
    public const string GroupName = "DG · автоматический меппинг (CONNECTOR)";

    public static string Place(GH_Document doc, IGH_Component connector, CanvasMappingRead read, MappingPlacementPlan plan)
    {
        if (plan.Classes.Count == 0)
        {
            return "nothing to place: no class has applied elements";
        }

        var added = new List<IGH_DocumentObject>();
        var bounds = doc.Objects.Where(o => o.Attributes is not null).Select(o => o.Attributes.Bounds).ToList();
        var x0 = (bounds.Count > 0 ? bounds.Max(b => b.Right) : connector.Attributes.Pivot.X) + 400f;
        var y0 = connector.Attributes.Pivot.Y;

        T Add<T>(T obj, float x, float y, string? nick = null) where T : IGH_DocumentObject
        {
            obj.CreateAttributes();
            if (nick is not null)
            {
                obj.NickName = nick;
            }

            obj.Attributes.Pivot = new PointF(x, y);
            doc.AddObject(obj, false);
            added.Add(obj);
            return obj;
        }

        static IGH_Param In(IGH_Component c, string name) => c.Params.Input.First(p => p.Name == name);
        static IGH_Param Out(IGH_Component c, string name) => c.Params.Output.First(p => p.Name == name);

        static void SetText(IGH_Param param, string value)
        {
            switch (param)
            {
                case Param_String text:
                    text.PersistentData.Clear();
                    text.PersistentData.Append(new GH_String(value));
                    break;
                case Param_GenericObject generic:
                    generic.PersistentData.Clear();
                    generic.PersistentData.Append(new GH_String(value));
                    break;
                default:
                    throw new InvalidOperationException($"cannot set text on {param.Name}");
            }
        }

        // Graph access: CONNECTOR.Database → GRAPH DECONSTRUCT → METAGRAPH.Rules.
        var graph = Add(new GraphDeconstructComponent(), x0, y0);
        In(graph, "Database").AddSource(Out(connector, "Database"));
        var metagraph = Add(new MetagraphComponent(), x0 + 220f, y0);
        In(metagraph, "Metagraph").AddSource(Out(graph, "Metagraph"));

        // One OBJECT STATE per class, bound by IRI.
        var objectStates = new Dictionary<string, IGH_Component>(StringComparer.Ordinal);
        var row = 0;
        foreach (var cls in plan.Classes)
        {
            var os = Add(new ObjectStateComponent(), x0 + 520f, y0 + 150f + 110f * row++, $"OS {cls.Label}");
            SetText(In(os, "Object"), MappingClassText.For(cls.ClassIri));
            var geometry = In(os, "Geometry");
            geometry.DataMapping = GH_DataMapping.Flatten;
            foreach (var stream in cls.Streams)
            {
                if (read.StreamParams.TryGetValue(stream, out var source))
                {
                    geometry.AddSource(source);
                }
            }

            objectStates[cls.ClassIri] = os;
        }

        // One RULE BY ID + PROPERTY STATE per rule binding.
        var ruleById = new List<IGH_Component>();
        var propertyStates = new List<IGH_Component>();
        row = 0;
        foreach (var b in plan.Bindings)
        {
            if (!objectStates.TryGetValue(b.ClassIri, out var os) || !read.MeasureParams.TryGetValue(b.MeasureParam, out var measure))
            {
                continue;
            }

            var y = y0 + 150f + 95f * row++;
            var rule = Add(new RuleByIdComponent(), x0 + 220f, y, $"R {b.RuleId}");
            In(rule, "Rules").AddSource(Out(metagraph, "Rules"));
            SetText(In(rule, "RuleId"), b.RuleId);
            ruleById.Add(rule);

            var ps = Add(new PropertyStateComponent(), x0 + 820f, y, $"PS {b.RuleId}");
            In(ps, "Rule").AddSource(Out(rule, "Rule"));
            SetText(In(ps, "DataProperty"), b.PropertyIri);
            var value = In(ps, "PropValue");
            value.DataMapping = GH_DataMapping.Flatten;
            value.AddSource(measure);
            var objState = In(ps, "ObjState");
            objState.DataMapping = GH_DataMapping.Flatten;
            objState.AddSource(Out(os, "ObjState"));
            propertyStates.Add(ps);
        }

        // PARAMETER STATE: one input per DG parameter, NickName = ParameterId = slider name.
        IGH_Component? paramState = null;
        var sliders = plan.Parameters.Where(p => read.Sliders.ContainsKey(p.SliderGuid)).ToList();
        if (sliders.Count > 0)
        {
            var pc = new ParameterStateComponent();
            paramState = Add(pc, x0 + 520f, y0 + 150f + 110f * plan.Classes.Count + 40f, "PARAMETER STATE (auto)");
            for (var i = 0; i < sliders.Count; i++)
            {
                IGH_Param input;
                if (i == 0)
                {
                    input = pc.Params.Input[0];
                }
                else
                {
                    input = pc.CreateParameter(GH_ParameterSide.Input, i);
                    pc.Params.RegisterInputParam(input, i);
                }

                input.Name = sliders[i].Name;
                input.NickName = sliders[i].Name;
                input.AddSource(read.Sliders[sliders[i].SliderGuid]);
            }

            pc.VariableParameterMaintenance();
            pc.Params.OnParametersChanged();
        }

        // DESIGN STATE ← all states; VALIDATOR ← every placed rule.
        var design = Add(new DesignStateCompositionComponent(), x0 + 1120f, y0 + 150f, "DESIGN STATE (auto)");
        var designObj = In(design, "ObjState");
        designObj.DataMapping = GH_DataMapping.Flatten;
        foreach (var os in objectStates.Values)
        {
            designObj.AddSource(Out(os, "ObjState"));
        }

        var designProp = In(design, "PropState");
        designProp.DataMapping = GH_DataMapping.Flatten;
        foreach (var ps in propertyStates)
        {
            designProp.AddSource(Out(ps, "PropState"));
        }

        if (paramState is not null)
        {
            In(design, "ParamState").AddSource(Out(paramState, "State"));
        }

        SetText(In(design, "DesignStateLabel"), read.DocumentKey);

        var validator = Add(new ValidatorComponent(), x0 + 1420f, y0 + 150f, "VALIDATOR (auto)");
        var validatorRule = In(validator, "Rule");
        foreach (var rule in ruleById)
        {
            validatorRule.AddSource(Out(rule, "Rule"));
        }

        In(validator, "DesignState").AddSource(Out(design, "DesignState"));
        var token = validator.Params.Input.FirstOrDefault(p => p.NickName == "Token" || p.Name == "Platform Token");
        token?.AddSource(Out(connector, "Session"));

        var group = new GH_Group { NickName = GroupName, Colour = Color.FromArgb(60, 21, 101, 192) };
        group.CreateAttributes();
        foreach (var obj in added)
        {
            group.AddObject(obj.InstanceGuid);
        }

        doc.AddObject(group, false);

        var note = plan.Notes.Count > 0 ? " · " + string.Join("; ", plan.Notes.Take(3)) : string.Empty;
        return $"placed {plan.Classes.Count} OBJECT STATE, {propertyStates.Count} PROPERTY STATE (+RULE BY ID), {(paramState is null ? 0 : sliders.Count)} parameters, DESIGN STATE, VALIDATOR{note}";
    }

    /// <summary>True when the document already has DG states placed (then nothing is placed again).</summary>
    public static bool HasStates(GH_Document doc) =>
        doc.Objects.Any(o => o is ObjectStateComponent || o is PropertyStateComponent || o is ValidatorComponent);
}
#endif
