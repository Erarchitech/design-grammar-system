using System.Text.Json;
using DG.Core.Mapping;

namespace DG.Tests;

/// <summary>
/// Phase 1303 plan 09 (D-37/D-38): calculation outputs, DG parameters and the placement plan.
/// Classes and rules are bound by identity, so the index-picker failure (classes added to the
/// ontology shift METAGRAPH Objects + List Item) cannot recur in placed components.
/// </summary>
public sealed class MappingPlacementTests
{
    [Fact]
    public void ClassText_RoundTrips_AndRejectsOtherText()
    {
        Assert.Equal("class:ex:HexagonalUnit", MappingClassText.For("ex:HexagonalUnit"));
        Assert.Equal("ex:HexagonalUnit", MappingClassText.Parse("  class:ex:HexagonalUnit "));
        Assert.Null(MappingClassText.Parse("HexagonalUnit"));
        Assert.Null(MappingClassText.Parse("class:"));
        Assert.Null(MappingClassText.Parse(null));
    }

    private static MappingApplyResult Applied(bool reversed = false)
    {
        var roles = new List<(string Id, string[] Roles, string Stream)>
        {
            ("e1", new[] { "ex:HexagonalUnit" }, "HU"),
            ("e2", new[] { "ex:HexagonalUnit" }, "HU"),
            ("e3", new[] { "ex:GlassPanel" }, "PB"),
            ("e4", new[] { "ex:GlassPanel", "ex:FacadeModule" }, "PX"),
            ("e5", new[] { "ex:GlassPanel" }, "SPLIT"),
            ("e6", new[] { "ex:Facade" }, "SPLIT"),
        };
        if (reversed)
        {
            roles.Reverse();
        }

        return new MappingApplyResult
        {
            RolesByElement = roles.ToDictionary(r => r.Id, r => (IReadOnlyList<string>)r.Roles),
            ElementStreams = roles.ToDictionary(r => r.Id, r => r.Stream),
            Parameters = new[] { new MappingParameterState("gh:doc:slider:aa11", "Module Width F1", "applied", null, null) },
            Bindings = new[]
            {
                new MappingRuleBinding("R_ASPECT_MIN", "ex:GlassPanel", "ex:hasAspectRatio", "gh:doc:measure:bb22", "PB"),
                new MappingRuleBinding("R_ORPHAN", "ex:Corridor", "ex:hasLength", "gh:doc:measure:cc33", "X"),
            },
        };
    }

    [Fact]
    public void Plan_BindsClassesToStreamsByIri_InAnyOrder()
    {
        var plan = MappingPlacementPlan.From(Applied());
        var again = MappingPlacementPlan.From(Applied(reversed: true));
        Assert.Equal(
            plan.Classes.Select(c => (c.ClassIri, string.Join(",", c.Streams))),
            again.Classes.Select(c => (c.ClassIri, string.Join(",", c.Streams))));
        var byClass = plan.Classes.ToDictionary(c => c.ClassIri);
        Assert.Equal(new[] { "HU" }, byClass["ex:HexagonalUnit"].Streams);
        // GlassPanel's rule is measured on PB only: PX would reach VALIDATOR without values.
        Assert.Equal(new[] { "PB" }, byClass["ex:GlassPanel"].Streams);
        Assert.Contains(plan.Notes, n => n.Contains("stream PX of class GlassPanel", StringComparison.Ordinal));
        Assert.Equal(new[] { "PX" }, byClass["ex:FacadeModule"].Streams);
        Assert.False(byClass.ContainsKey("ex:Facade"));
        Assert.Contains(plan.Notes, n => n.Contains("SPLIT", StringComparison.Ordinal));
        Assert.Equal("HexagonalUnit", byClass["ex:HexagonalUnit"].Label);
    }

    [Fact]
    public void Plan_PlacesOneObjectStatePerMeasuredStream()
    {
        var applied = new MappingApplyResult
        {
            RolesByElement = new Dictionary<string, IReadOnlyList<string>>
            {
                ["a1"] = new[] { "ex:HexagonalUnit" },
                ["b1"] = new[] { "ex:HexagonalUnit" },
            },
            ElementStreams = new Dictionary<string, string> { ["a1"] = "M6", ["b1"] = "M5" },
            Bindings = new[]
            {
                new MappingRuleBinding("R_GAP", "ex:HexagonalUnit", "ex:hasGapCount", "gh:doc:measure:g6", "M6"),
                new MappingRuleBinding("R_VC", "ex:HexagonalUnit", "ex:hasVertexCount", "gh:doc:measure:v6", "M6"),
                new MappingRuleBinding("R_GAP5", "ex:HexagonalUnit", "ex:hasGapCount", "gh:doc:measure:g5", "M5"),
                new MappingRuleBinding("R_ELSE", "ex:HexagonalUnit", "ex:hasGapCount", "gh:doc:measure:g0", "ELSEWHERE"),
            },
        };
        var plan = MappingPlacementPlan.From(applied);
        Assert.Equal(new[] { "M5", "M6" }, plan.Classes.Select(c => Assert.Single(c.Streams)).OrderBy(s => s, StringComparer.Ordinal));
        Assert.All(plan.Classes, c => Assert.Equal("ex:HexagonalUnit", c.ClassIri));
        Assert.Equal(new[] { "R_GAP", "R_GAP5", "R_VC" }, plan.Bindings.Select(b => b.RuleId));
        Assert.Contains(plan.Notes, n => n.Contains("R_ELSE", StringComparison.Ordinal) && n.Contains("ELSEWHERE", StringComparison.Ordinal));
    }

    [Fact]
    public void WholeStreamGuard_NeverIncludesUnacceptedRemainder()
    {
        var snapshot = new MappingSnapshot
        {
            Elements = Enumerable.Range(1, 10).Select(i => new MappingElement { NativeId = $"e{i}", Stream = "S" }).ToList(),
        };
        MappingApplyResult Selection(int count) => new()
        {
            RolesByElement = Enumerable.Range(1, count).ToDictionary(i => $"e{i}", _ => (IReadOnlyList<string>)new[] { "ex:GlassPanel" }),
            ElementStreams = Enumerable.Range(1, count).ToDictionary(i => $"e{i}", _ => "S"),
        };
        Assert.False(MappingPlacementPlan.CoversWholeStreams(Selection(4), snapshot));
        Assert.True(MappingPlacementPlan.CoversWholeStreams(Selection(10), snapshot));
        Assert.False(MappingPlacementPlan.CoversWholeStreams(Selection(11), snapshot));
        var separate = new MappingSnapshot
        {
            Elements = Enumerable.Range(1, 10).Select(i => new MappingElement { NativeId = $"e{i}", Stream = i <= 4 ? "S" : "Other" }).ToList(),
        };
        Assert.True(MappingPlacementPlan.CoversWholeStreams(Selection(4), separate));
    }

    [Fact]
    public void ExactSelection_FourOfTenAndSplitRoles_DoNotExpandTheStream()
    {
        var snapshot = new MappingSnapshot
        {
            Elements = Enumerable.Range(0, 10).Select(i => new MappingElement { NativeId = $"e{i}", Stream = "S" }).ToArray(),
        };
        var applied = new MappingApplyResult
        {
            RolesByElement = Enumerable.Range(0, 4).ToDictionary(i => $"e{i}", i => (IReadOnlyList<string>)new[] { i < 2 ? "ex:A" : "ex:B" }),
            ElementStreams = Enumerable.Range(0, 4).ToDictionary(i => $"e{i}", _ => "S"),
        };
        var classes = MappingSelection.Classes(applied, snapshot);
        Assert.Equal(new[] { "e0", "e1" }, classes.Single(c => c.ClassIri == "ex:A").ElementIds);
        Assert.Equal(new[] { "e2", "e3" }, classes.Single(c => c.ClassIri == "ex:B").ElementIds);
        Assert.Equal(4, classes.Sum(c => c.ElementIds.Count));
        var addresses = Enumerable.Range(0, 10).ToDictionary(i => $"e{i}", i => new MappingSourceAddress("{0}", i, false));
        var selected = MappingSelection.Addresses(classes.SelectMany(c => c.ElementIds), addresses);
        Assert.Equal(new[] { 0, 1, 2, 3 }, selected.Select(a => a.Index));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Addresses(new[] { "e0", "unknown" }, addresses));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Addresses(new[] { "e0", "e0" }, addresses));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Classes(new MappingApplyResult
        {
            RolesByElement = applied.RolesByElement,
            ElementStreams = applied.ElementStreams.ToDictionary(kv => kv.Key, _ => "other"),
        }, snapshot));
    }

    [Fact]
    public void SourceResolution_PreservesBranchMembersAndPairsOnlyTheirMeasure()
    {
        var tree = new Dictionary<string, IReadOnlyList<int>> { ["{0}"] = new[] { 10, 11, 12, 13, 14, 15 } };
        var items = new[] { new MappingSourceAddress("{0}", 1, false), new MappingSourceAddress("{0}", 4, false) };
        Assert.Equal(new[] { 11, 14 }, MappingSelection.Resolve(items, tree, false).Select(r => Assert.Single(r)));
        var branch = new[] { new MappingSourceAddress("{0}", 0, true) };
        Assert.Equal(tree["{0}"], Assert.Single(MappingSelection.Resolve(branch, tree, false)));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Resolve(branch, tree, true));
        var values = new Dictionary<string, IReadOnlyList<int>> { ["{0}"] = new[] { 99 } };
        Assert.Equal(99, Assert.Single(Assert.Single(MappingSelection.Resolve(branch, values, true))));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Resolve(items, values, true));
    }

    [Fact]
    public void PartialHistory_BindsOnlyCommittedObjectsAndMeasures_AndRejectsReplay()
    {
        var first = new MappingApplyResult
        {
            RolesByElement = new Dictionary<string, IReadOnlyList<string>> { ["e1"] = new[] { "ex:A" } },
            ElementStreams = new Dictionary<string, string> { ["e1"] = "S" },
        };
        var binding = new MappingRuleBinding("R", "ex:A", "ex:p", "m", "S");
        var second = new MappingApplyResult
        {
            Measures = new[] { new MappingMeasureState("m", "Measure", "applied", "p", "ex:p", "S") },
            Bindings = new[] { binding, binding with { ClassIri = "ex:Unaccepted" } },
        };
        var merged = MappingSelection.Append(first, second);
        Assert.Equal(binding, Assert.Single(merged.Bindings));
        Assert.Equal("e1", Assert.Single(merged.RolesByElement).Key);
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Append(merged, first));
        Assert.Throws<InvalidOperationException>(() => MappingSelection.Append(merged, second));
        var sliders = MappingSelection.Append(merged, new MappingApplyResult
        {
            Parameters = new[] { new MappingParameterState("slider", "Width", "applied", null, null) },
        });
        Assert.Single(sliders.Parameters);
        Assert.Single(sliders.RolesByElement);
        Assert.Single(sliders.Measures);
    }

    [Fact]
    public void StreamDedupe_DropsDuplicatesAndUnions()
    {
        var found = MappingStreamDedupe.Find(new (string, string, IReadOnlyCollection<string>)[]
        {
            ("A", "Panels A", new[] { "a1", "a2", "a3" }),
            ("B", "Panels B", new[] { "b1", "b2" }),
            ("ALL", "All panels", new[] { "a1", "a2", "a3", "b1", "b2" }),
            ("F1", "bbox F", new[] { "f" }),
            ("F2", "bbox F", new[] { "f" }),
            ("H", "Hex", new[] { "h1", "h2", "a1" }),
            ("M6", "6-Module contours", new[] { "curve|m1", "curve|m2" }),
            ("M5", "5-Module contours", new[] { "curve|m3" }),
            ("MS", "modules", new[] { "surface|m1", "surface|m2", "surface|m3" }),
            ("MC", "module outlines", new[] { "curve|m1", "curve|m2", "curve|m3", "curve|m9" }),
            ("MD", "module copy", new[] { "surface|m1", "surface|m2", "surface|m3" }),
        });
        Assert.Equal(new[] { "ALL", "F2", "MC", "MD", "MS" }, found.Keys.OrderBy(k => k, StringComparer.Ordinal));
        Assert.Equal("union of Panels A + Panels B", found["ALL"]);
        Assert.Equal("same elements as bbox F", found["F2"]);
        Assert.Equal("same elements as modules", found["MD"]);
        Assert.Equal("union of 6-Module contours + 5-Module contours", found["MS"]);
        Assert.Empty(MappingStreamDedupe.Find(new (string, string, IReadOnlyCollection<string>)[] { ("A", "a", new[] { "x" }), ("B", "b", Array.Empty<string>()) }));
    }

    [Fact]
    public void Plan_KeepsBindingsOfPlacedClassesAndTheSliders()
    {
        var plan = MappingPlacementPlan.From(Applied());
        var binding = Assert.Single(plan.Bindings);
        Assert.Equal(("R_ASPECT_MIN", "bb22", "ex:hasAspectRatio"), (binding.RuleId, binding.MeasureParam, binding.PropertyIri));
        Assert.Contains(plan.Notes, n => n.Contains("R_ORPHAN", StringComparison.Ordinal));
        var parameter = Assert.Single(plan.Parameters);
        Assert.Equal(("aa11", "Module Width F1"), (parameter.SliderGuid, parameter.Name));
    }

    [Fact]
    public void MeasureMatcher_PairsByPathsAndAgreement()
    {
        var elements = new Dictionary<string, IReadOnlyDictionary<string, object>>
        {
            [MappingMeasureMatcher.Key("{0;0}", 0)] = new Dictionary<string, object> { ["hasAspectRatio"] = 2.5, ["hasVertexCount"] = 4 },
            [MappingMeasureMatcher.Key("{0;1}", 0)] = new Dictionary<string, object> { ["hasAspectRatio"] = 3.0, ["hasVertexCount"] = 4 },
        };
        var ar = new Dictionary<string, double> { ["{0;0}|0"] = 2.5000001, ["{0;1}|0"] = 3.0 };
        var m = MappingMeasureMatcher.Match("PB", ar, elements);
        Assert.True(m.PathMatch);
        Assert.False(m.Constant);
        Assert.Equal(1.0, m.Agreement["hasAspectRatio"]);
        Assert.False(m.Agreement.ContainsKey("hasVertexCount"));

        var vc = MappingMeasureMatcher.Match("PB", new Dictionary<string, double> { ["{0;0}|0"] = 4, ["{0;1}|0"] = 4 }, elements);
        Assert.True(vc.Constant);
        Assert.Equal(1.0, vc.Agreement["hasVertexCount"]);

        var other = MappingMeasureMatcher.Match("PB", new Dictionary<string, double> { ["{1}|0"] = 7 }, elements);
        Assert.False(other.PathMatch);
        Assert.Empty(other.Agreement);
    }

    [Fact]
    public void Snapshot_SendsStreamsMeasuresAndAsksForTheLlm()
    {
        var snapshot = new MappingSnapshot
        {
            Elements = new[] { new MappingElement { NativeId = "e1", Source = "join HU", Stream = "HU" } },
            Measures = new[]
            {
                new MappingMeasure
                {
                    NativeId = "gh:doc:measure:bb22", Name = "AR", Component = "measure", Count = 125, Min = 1.4, Max = 5.5,
                    Streams = new[] { new MappingMeasureStream { Stream = "PB", PathMatch = true, Agreement = new Dictionary<string, double> { ["hasAspectRatio"] = 1.0 } } },
                },
            },
        };
        using var doc = JsonDocument.Parse(snapshot.ToRequestJson("v12", "x"));
        var root = doc.RootElement;
        Assert.True(root.GetProperty("context").GetProperty("llm").GetBoolean());
        Assert.Equal("HU", root.GetProperty("elements")[0].GetProperty("stream").GetString());
        var measure = root.GetProperty("measures")[0];
        Assert.Equal("AR", measure.GetProperty("name").GetString());
        Assert.Equal(1.0, measure.GetProperty("streams")[0].GetProperty("agreement").GetProperty("hasAspectRatio").GetDouble());
        Assert.False(new MappingSnapshot { Measures = snapshot.Measures }.IsEmpty);
        Assert.NotEqual(snapshot.Fingerprint(), new MappingSnapshot { Elements = snapshot.Elements }.Fingerprint());
    }

    [Fact]
    public void ParseApply_ReadsStreamsBindingsAndParameters()
    {
        const string json = """
        {"elements":[{"nativeId":"e1","roles":["ex:HexagonalUnit"],"stream":"HU"}],
         "parameters":[{"nativeId":"gh:doc:slider:aa11","name":"Module Width F1"}],
         "measures":[{"nativeId":"gh:doc:measure:bb22","name":"AR","propertyIri":"ex:hasAspectRatio","stream":"PB"}],
         "bindings":[{"ruleId":"R1","classLocal":"GlassPanel","classIri":"ex:GlassPanel","propertyIri":"ex:hasAspectRatio","measureId":"gh:doc:measure:bb22","stream":"PB"}]}
        """;
        var applied = MappingSessionClient.ParseApply(json);
        Assert.Equal("HU", applied.ElementStreams["e1"]);
        Assert.Equal("Module Width F1", Assert.Single(applied.Parameters).Name);
        Assert.Equal("hasAspectRatio", Assert.Single(applied.Measures).PropertyLabel);
        Assert.Equal("ex:GlassPanel", Assert.Single(applied.Bindings).ClassIri);
    }
}
