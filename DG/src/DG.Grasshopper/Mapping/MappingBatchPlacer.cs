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

/// <summary>Session-owned placement. Later batches add only new selections and bindings.</summary>
internal sealed class MappingBatchPlacer
{
    private sealed record Objects(string Class, string Stream, IReadOnlyList<string> Ids, IGH_Component Component);
    private readonly List<Objects> _objects = new();
    private readonly HashSet<(Guid Object, string Rule, string Property, string Measure)> _bindings = new();
    private readonly HashSet<string> _parameters = new(StringComparer.Ordinal);
    private readonly List<IGH_DocumentObject> _owned = new();
    private IGH_Component? _metagraph;
    private IGH_Component? _design;
    private IGH_Component? _validator;
    private readonly List<(IGH_Param Output, int Count)> _verification = new();

    public bool VerifyLastDelivery() => _verification.All(v => v.Output.VolatileDataCount == v.Count)
        && _owned.OfType<MappingSubsetComponent>().All(c => !c.RuntimeMessages(GH_RuntimeMessageLevel.Error).Any());

    public bool IsIntact(GH_Document doc) => _owned.All(o => doc.Objects.Contains(o));

    public string Place(GH_Document doc, IGH_Component connector, CanvasMappingRead read,
        MappingApplyResult current, MappingApplyResult cumulative)
    {
        if (!IsIntact(doc)) throw new InvalidOperationException("An owned mapping component was removed");
        var classes = MappingSelection.Classes(current, read.Snapshot);
        foreach (var cls in classes)
        {
            _ = MappingSelection.Addresses(cls.ElementIds, read.Addresses);
            if (!read.StreamParams.ContainsKey(cls.Stream)) throw new InvalidOperationException("Missing stream");
        }

        foreach (var p in current.Parameters)
            if (!read.Sliders.ContainsKey(MappingPlacementPlan.LastSegment(p.NativeId)))
                throw new InvalidOperationException("Missing slider");
        foreach (var b in cumulative.Bindings)
            if (!read.MeasureParams.ContainsKey(MappingPlacementPlan.LastSegment(b.MeasureId)))
                throw new InvalidOperationException("Missing calculation output");
        foreach (var m in current.Measures)
            if (!cumulative.Bindings.Any(b => b.MeasureId == m.NativeId))
                throw new InvalidOperationException("Accepted measure has no committed object/rule binding yet");

        _verification.Clear();
        var added = new List<IGH_DocumentObject>();
        var linked = new List<(IGH_Param Input, IGH_Param Source)>();
        var newObjects = new List<Objects>();
        var newBindings = new HashSet<(Guid, string, string, string)>();
        var newParameters = new List<string>();
        var x = doc.Objects.Where(o => o.Attributes is not null).Select(o => o.Attributes.Bounds.Right)
            .DefaultIfEmpty(connector.Attributes.Pivot.X).Max() + 250f;
        var y = connector.Attributes.Pivot.Y;
        var row = 0;
        T Add<T>(T obj, float dx, string? nick = null) where T : IGH_DocumentObject
        {
            obj.CreateAttributes();
            if (nick is not null) obj.NickName = nick;
            obj.Attributes.Pivot = new PointF(x + dx, y + 100f * row++);
            added.Add(obj); // also track an AddObject that throws after a partial insertion
            doc.AddObject(obj, false);
            return obj;
        }
        static IGH_Param In(IGH_Component c, string name) => c.Params.Input.First(p => p.Name == name);
        static IGH_Param Out(IGH_Component c, string name) => c.Params.Output.First(p => p.Name == name);
        void Link(IGH_Param input, IGH_Param source)
        {
            linked.Add((input, source));
            input.AddSource(source);
        }
        static void Text(IGH_Param p, string value)
        {
            if (p is Param_String text) text.PersistentData.Append(new GH_String(value));
            else if (p is Param_GenericObject generic) generic.PersistentData.Append(new GH_String(value));
            else throw new InvalidOperationException("Unsupported text input");
        }
        IGH_Component Select(IGH_Param source, IReadOnlyList<string> ids, bool measure, string classIri)
        {
            var selection = Add(new MappingSubsetComponent(), 0, measure ? "Committed values" : "Committed geometry");
            selection.Configure(MappingSelection.Addresses(ids, read.Addresses), measure, ids, classIri,
                MappingCanvasReader.DataSignature(source.VolatileData));
            _verification.Add((Out(selection, "Selected"), ids.Count));
            Link(In(selection, "Source"), source);
            return selection;
        }

        var metagraph = _metagraph;
        var design = _design;
        var validator = _validator;
        try
        {
            if (metagraph is null)
            {
                var graph = Add(new GraphDeconstructComponent(), 0);
                Link(In(graph, "Database"), Out(connector, "Database"));
                metagraph = Add(new MetagraphComponent(), 220);
                Link(In(metagraph, "Metagraph"), Out(graph, "Metagraph"));
                design = Add(new DesignStateCompositionComponent(), 1120, "DESIGN STATE (confirmed mapping)");
                Text(In(design, "DesignStateLabel"), read.DocumentKey);
                validator = Add(new ValidatorComponent(), 1420, "VALIDATOR (confirmed mapping)");
                Link(In(validator, "DesignState"), Out(design, "DesignState"));
                var token = validator.Params.Input.FirstOrDefault(p => p.NickName == "Token" || p.Name == "Platform Token");
                if (token is not null) Link(token, Out(connector, "Session"));
            }

            foreach (var cls in classes)
            {
                var selected = Select(read.StreamParams[cls.Stream], cls.ElementIds, false, cls.ClassIri);
                var os = Add(new ObjectStateComponent(), 520, $"OS {MappingSessionClient.LocalName(cls.ClassIri)}");
                Link(In(os, "Object"), Out(selected, "Objects"));
                Link(In(os, "Geometry"), Out(selected, "Selected"));
                Link(In(design!, "ObjState"), Out(os, "ObjState"));
                _verification.Add((Out(os, "ObjState"), cls.ElementIds.Count));
                newObjects.Add(new Objects(cls.ClassIri, cls.Stream, cls.ElementIds, os));
            }

            foreach (var b in cumulative.Bindings)
            {
                foreach (var obj in _objects.Concat(newObjects).Where(o => o.Class == b.ClassIri && o.Stream == b.Stream))
                {
                    var key = (obj.Component.InstanceGuid, b.RuleId, b.PropertyIri, b.MeasureId);
                    if (_bindings.Contains(key) || !newBindings.Add(key)) continue;
                    var selected = Select(read.MeasureParams[MappingPlacementPlan.LastSegment(b.MeasureId)], obj.Ids, true, b.ClassIri);
                    var rule = Add(new RuleByIdComponent(), 220, $"R {b.RuleId}");
                    Link(In(rule, "Rules"), Out(metagraph, "Rules"));
                    Text(In(rule, "RuleId"), b.RuleId);
                    var ps = Add(new PropertyStateComponent(), 820, $"PS {b.RuleId}");
                    Link(In(ps, "Rule"), Out(rule, "Rule"));
                    Text(In(ps, "DataProperty"), b.PropertyIri);
                    Link(In(ps, "PropValue"), Out(selected, "Selected"));
                    Link(In(ps, "ObjState"), Out(obj.Component, "ObjState"));
                    Link(In(design!, "PropState"), Out(ps, "PropState"));
                    _verification.Add((Out(ps, "PropState"), obj.Ids.Count));
                    Link(In(validator!, "Rule"), Out(rule, "Rule"));
                }
            }

            var sliders = current.Parameters.Where(p => !_parameters.Contains(p.NativeId)).ToList();
            if (sliders.Count > 0)
            {
                var pc = Add(new ParameterStateComponent(), 520, "PARAMETER STATE (confirmed mapping)");
                for (var i = 0; i < sliders.Count; i++)
                {
                    var input = i == 0 ? pc.Params.Input[0] : pc.CreateParameter(GH_ParameterSide.Input, i);
                    if (i > 0) pc.Params.RegisterInputParam(input, i);
                    input.Name = input.NickName = sliders[i].Name;
                    Link(input, read.Sliders[MappingPlacementPlan.LastSegment(sliders[i].NativeId)]);
                    newParameters.Add(sliders[i].NativeId);
                }
                pc.VariableParameterMaintenance();
                pc.Params.OnParametersChanged();
                Link(In(design!, "ParamState"), Out(pc, "State"));
                _verification.Add((Out(pc, "State"), 1));
            }

            var group = Add(new GH_Group { Colour = Color.FromArgb(60, 21, 101, 192) }, 0, "DG · confirmed mapping batch");
            foreach (var obj in added.Where(o => !ReferenceEquals(o, group))) group.AddObject(obj.InstanceGuid);
            foreach (var input in linked.Select(l => l.Input).Distinct()) input.ExpireSolution(false);
            _metagraph = metagraph;
            _design = design;
            _validator = validator;
            _owned.AddRange(added);
            _objects.AddRange(newObjects);
            _bindings.UnionWith(newBindings);
            _parameters.UnionWith(newParameters);
            return $"added {current.RolesByElement.Count} committed elements, {newBindings.Count} property bindings, {newParameters.Count} parameters";
        }
        catch
        {
            // Best-effort cleanup only; the caller retains an uncertain journal entry and never replays.
            foreach (var (input, source) in linked.AsEnumerable().Reverse()) input.RemoveSource(source);
            foreach (var obj in added.AsEnumerable().Reverse())
                if (doc.Objects.Contains(obj)) doc.RemoveObject(obj, false);
            throw;
        }
    }
}
#endif
