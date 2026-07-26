using System.Text.Json;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;
using DG.Core.Serialization;

namespace DG.Tests;

/// <summary>
/// Phase 36 UAT F6 -- provider/model/confidence must survive the whole recognized-entity
/// provenance chain: the canvas ValueTable marker written at accept time -> the extractor's
/// <see cref="RawGroup"/> -> the parser's typed Cg* entity -> the cgContextJson wire envelope
/// that <c>computgraph_publish.py</c> reads. Before F6 the marker was the literal string
/// <c>"true"</c>, so the model identity and confidence score were discarded at confirm time and
/// every recognized node published with those three properties null.
///
/// <para>
/// These tests cover every GH-free link. The two GH-only links (StructureConfirmComponent's
/// marker write, CanvasContextExtractor's marker read) are unreachable from DG.Tests, which does
/// not reference DG.Grasshopper -- but both are one call each to the
/// <see cref="RecognitionMarker"/> methods pinned below, so the untested surface is the call
/// site, not the format.
/// </para>
/// </summary>
public sealed class RecognitionProvenanceFlowTests
{
    // ── RecognitionMarker: the on-canvas format ──

    [Fact]
    public void Marker_RoundTripsProviderModelAndConfidence()
    {
        var serialized = RecognitionMarker.Serialize("anthropic", "claude-opus-4-6", 0.87);

        var provenance = RecognitionMarker.TryParse(serialized);

        Assert.NotNull(provenance);
        Assert.Equal("anthropic", provenance!.Provider);
        Assert.Equal("claude-opus-4-6", provenance.Model);
        Assert.Equal(0.87, provenance.Confidence);
    }

    [Fact]
    public void Marker_LegacyTrueLiteral_StaysRecognizedWithNullProvenance()
    {
        // A canvas saved before F6 must keep source:recognized -- exactly the state it was
        // saved in, no invented provenance.
        var provenance = RecognitionMarker.TryParse("true");

        Assert.NotNull(provenance);
        Assert.Null(provenance!.Provider);
        Assert.Null(provenance.Model);
        Assert.Null(provenance.Confidence);
    }

    [Fact]
    public void Marker_WithNoProvenance_SerializesToTheLegacyLiteral()
    {
        // Never wrap three nulls in a JSON envelope -- a provenance-less accept is byte-identical
        // to what pre-F6 builds wrote, so such a canvas stays readable by them.
        Assert.Equal("true", RecognitionMarker.Serialize(null, null, null));
        Assert.Equal("true", RecognitionMarker.Serialize("   ", "", null));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("false")]
    [InlineData("not json and not true")]
    [InlineData("{ this is not valid json")]
    public void Marker_AbsentOrUnreadable_IsNotRecognized(string? rawValue)
    {
        Assert.Null(RecognitionMarker.TryParse(rawValue));
    }

    [Fact]
    public void Marker_PartialProvenance_KeepsTheFieldsItHas()
    {
        var provenance = RecognitionMarker.TryParse(RecognitionMarker.Serialize("ollama", null, null));

        Assert.NotNull(provenance);
        Assert.Equal("ollama", provenance!.Provider);
        Assert.Null(provenance.Model);
        Assert.Null(provenance.Confidence);
    }

    [Fact]
    public void Marker_KeyMatchesTheDocumentedValueTableKey()
    {
        var guid = new Guid("A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14");

        // Pinned: changing this orphans every marker on every saved canvas.
        Assert.Equal($"dg.recognized.{guid}", RecognitionMarker.Key(guid));
    }

    // ── Parser: RawGroup provenance -> typed Cg* entity ──

    [Fact]
    public void Parse_RecognizedGroups_CarryProvenanceOntoEveryEntityKind()
    {
        var raw = new RawCanvas
        {
            Definition = new CgDefinition { DocumentId = "doc-1", FileName = "frame.gh" },
            Groups =
            {
                RecognizedGroup("11_Proc - 2D Truss Configuration", "n1"),
                RecognizedGroup("11_Pat_1 Split", "n2"),
                RecognizedGroup("11_Var_SpansCount", "n3"),
                RecognizedGroup("11_IntF_ParSplitAt", "n4"),
            },
            Nodes =
            {
                new CgNode { InstanceId = "n3", Name = "Number Slider", Nickname = "SpansCount" },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);
        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);

        AssertProvenance(procedure.Source, procedure.Provider, procedure.Model, procedure.Confidence);

        var pattern = procedure.Patterns.Single();
        AssertProvenance(pattern.Source, pattern.Provider, pattern.Model, pattern.Confidence);

        var parameter = procedure.Parameters.Single();
        AssertProvenance(parameter.Source, parameter.Provider, parameter.Model, parameter.Confidence);

        var iface = procedure.Interfaces.Single();
        AssertProvenance(iface.Source, iface.Provider, iface.Model, iface.Confidence);
    }

    [Fact]
    public void Parse_TaggedGroup_HasNoProvenance()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" } } },
        };

        var procedure = CanvasAnnotationParser.Parse(raw).Algorithms.Single().Procedures.Single();

        Assert.Equal("tagged", procedure.Source);
        Assert.Null(procedure.Provider);
        Assert.Null(procedure.Model);
        Assert.Null(procedure.Confidence);
    }

    // ── Serializer: typed entity -> the wire envelope computgraph_publish.py reads ──

    [Fact]
    public void Serialize_EmitsProvenanceKeysPublishReads()
    {
        var raw = new RawCanvas
        {
            Definition = new CgDefinition { DocumentId = "doc-1", FileName = "frame.gh" },
            Groups = { RecognizedGroup("11_Proc - 2D Truss Configuration", "n1") },
        };

        var json = ComputgraphContextSerializer.Serialize(CanvasAnnotationParser.Parse(raw));

        using var doc = JsonDocument.Parse(json);
        var procedure = doc.RootElement.GetProperty("algorithms")[0].GetProperty("procedures")[0];

        // These three key names are the contract with computgraph_publish.py's
        // procedure.get("provider")/.get("model")/.get("confidence").
        Assert.Equal("anthropic", procedure.GetProperty("provider").GetString());
        Assert.Equal("claude-opus-4-6", procedure.GetProperty("model").GetString());
        Assert.Equal(0.87, procedure.GetProperty("confidence").GetDouble());
    }

    [Fact]
    public void Deserialize_RestoresProvenance_RoundTrip()
    {
        var raw = new RawCanvas
        {
            Definition = new CgDefinition { DocumentId = "doc-1", FileName = "frame.gh" },
            Groups =
            {
                RecognizedGroup("11_Proc - 2D Truss Configuration", "n1"),
                RecognizedGroup("11_Pat_1 Split", "n2"),
                RecognizedGroup("11_IntF_ParSplitAt", "n4"),
            },
        };

        var json = ComputgraphContextSerializer.Serialize(CanvasAnnotationParser.Parse(raw));
        var restored = ComputgraphContextSerializer.Deserialize(json);

        var procedure = restored.Algorithms.Single().Procedures.Single();
        AssertProvenance(procedure.Source, procedure.Provider, procedure.Model, procedure.Confidence);

        var pattern = procedure.Patterns.Single();
        AssertProvenance(pattern.Source, pattern.Provider, pattern.Model, pattern.Confidence);

        var iface = procedure.Interfaces.Single();
        AssertProvenance(iface.Source, iface.Provider, iface.Model, iface.Confidence);
    }

    [Fact]
    public void Serialize_TaggedEntity_LeavesProvenanceKeysNull()
    {
        var raw = new RawCanvas
        {
            Definition = new CgDefinition { DocumentId = "doc-1", FileName = "frame.gh" },
            Groups = { new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" } } },
        };

        var json = ComputgraphContextSerializer.Serialize(CanvasAnnotationParser.Parse(raw));

        using var doc = JsonDocument.Parse(json);
        var procedure = doc.RootElement.GetProperty("algorithms")[0].GetProperty("procedures")[0];

        Assert.Equal("tagged", procedure.GetProperty("source").GetString());
        Assert.Equal(JsonValueKind.Null, procedure.GetProperty("provider").ValueKind);
        Assert.Equal(JsonValueKind.Null, procedure.GetProperty("model").ValueKind);
        Assert.Equal(JsonValueKind.Null, procedure.GetProperty("confidence").ValueKind);
    }

    // ── Helpers ──

    /// <summary>
    /// A group as the extractor produces it after reading a post-F6 recognition marker.
    /// </summary>
    private static RawGroup RecognizedGroup(string nickname, string memberId) => new()
    {
        Nickname = nickname,
        MemberIds = { memberId },
        Recognized = true,
        Provider = "anthropic",
        Model = "claude-opus-4-6",
        Confidence = 0.87,
    };

    private static void AssertProvenance(string source, string? provider, string? model, double? confidence)
    {
        Assert.Equal("recognized", source);
        Assert.Equal("anthropic", provider);
        Assert.Equal("claude-opus-4-6", model);
        Assert.Equal(0.87, confidence);
    }
}
