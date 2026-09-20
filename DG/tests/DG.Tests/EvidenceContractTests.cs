using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using DG.Core.Contracts;

namespace DG.Tests;

public sealed class EvidenceContractTests
{
    /// <summary>
    /// Walks up from the test assembly's output directory to the repo root, so this test works
    /// regardless of build configuration (Debug/Release) or target framework subfolder.
    /// </summary>
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "spec", "evidence-contract.schema.json")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException($"EvidenceContractTests.FindRepoRoot: could not locate repo root (spec/evidence-contract.schema.json) walking up from {AppContext.BaseDirectory}.");
    }

    private static JsonNode LoadSchema()
    {
        var repoRoot = FindRepoRoot();
        var schemaPath = Path.Combine(repoRoot, "spec", "evidence-contract.schema.json");
        var text = File.ReadAllText(schemaPath);
        return JsonNode.Parse(text) ?? throw new InvalidOperationException("evidence-contract.schema.json parsed to null.");
    }

    [Fact]
    public void EvidenceStatus_ShouldHaveExactlyEightMembers()
    {
        Assert.Equal(8, Enum.GetValues<EvidenceStatus>().Length);
    }

    [Fact]
    public void ToWireName_ShouldMapNoPopulation_ToSnakeCase()
    {
        Assert.Equal("no_population", EvidenceStatusNames.ToWireName(EvidenceStatus.NoPopulation));
    }

    [Fact]
    public void ToWireName_ShouldMapNotEvaluated_ToSnakeCase()
    {
        Assert.Equal("not_evaluated", EvidenceStatusNames.ToWireName(EvidenceStatus.NotEvaluated));
    }

    [Fact]
    public void EvidenceStatusWireNames_ShouldMatchSchemaEnum_Exactly()
    {
        var schema = LoadSchema();
        var enumNode = schema["$defs"]!["CanonicalStatus"]!["enum"]!.AsArray();
        var schemaNames = enumNode.Select(n => n!.GetValue<string>()).ToHashSet(StringComparer.Ordinal);

        var csharpNames = EvidenceStatusNames.AllWireNames.ToHashSet(StringComparer.Ordinal);

        Assert.Equal(schemaNames, csharpNames);
    }

    private sealed class StatusCarrier
    {
        [System.Text.Json.Serialization.JsonConverter(typeof(EvidenceStatusJsonConverter))]
        public EvidenceStatus Status { get; set; }
    }

    [Fact]
    public void Serialization_ShouldRoundTrip_NoPopulation_AsSnakeCaseWireForm()
    {
        var carrier = new StatusCarrier { Status = EvidenceStatus.NoPopulation };

        var json = JsonSerializer.Serialize(carrier);

        Assert.Contains("\"no_population\"", json);

        var roundTripped = JsonSerializer.Deserialize<StatusCarrier>(json);
        Assert.NotNull(roundTripped);
        Assert.Equal(EvidenceStatus.NoPopulation, roundTripped!.Status);
    }

    [Fact]
    public void Deserialization_ShouldThrowJsonException_ForUnrecognizedStatus()
    {
        var badJson = "{\"Status\":\"totally_bogus\"}";

        var ex = Assert.Throws<JsonException>(() => JsonSerializer.Deserialize<StatusCarrier>(badJson));
        Assert.Contains("totally_bogus", ex.Message);
    }

    [Fact]
    public void DGTests_ShouldReach_SharedGoldenFixture()
    {
        var fixturePath = Path.Combine(AppContext.BaseDirectory, "Fixtures", "golden", "fixture.json");

        Assert.True(File.Exists(fixturePath), $"Expected shared golden fixture copied to test output at {fixturePath}. Confirm the DG.Tests.csproj repo-root <None Include> rule is present and the project has been rebuilt.");
    }

    private static EvidenceRow Row(string objectId, string ruleId, EvidenceStatus status)
    {
        return new EvidenceRow { ObjectId = objectId, RuleId = ruleId, CanonicalStatus = status };
    }

    [Fact]
    public void Build_ShouldSortRows_ByObjectIdThenRuleId_Ordinal()
    {
        var rows = new List<EvidenceRow>
        {
            Row("OBJ_B", "R_2", EvidenceStatus.Passed),
            Row("OBJ_A", "R_2", EvidenceStatus.Passed),
            Row("OBJ_A", "R_1", EvidenceStatus.Passed),
        };

        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "dg-grasshopper-evaluator", "1.0", "test-stage", rows);

        Assert.Equal(3, envelope.Rows.Count);
        Assert.Equal(("OBJ_A", "R_1"), (envelope.Rows[0].ObjectId, envelope.Rows[0].RuleId));
        Assert.Equal(("OBJ_A", "R_2"), (envelope.Rows[1].ObjectId, envelope.Rows[1].RuleId));
        Assert.Equal(("OBJ_B", "R_2"), (envelope.Rows[2].ObjectId, envelope.Rows[2].RuleId));
    }

    [Fact]
    public void Build_ShouldSetContractAndCanonicalizationVersion()
    {
        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "svc", "1.0", "stage", new List<EvidenceRow>
        {
            Row("OBJ_A", "R_1", EvidenceStatus.Passed),
        });

        Assert.Equal("1.0.0", envelope.ContractVersion);
        Assert.Equal(CanonicalJsonWriter.CanonicalizationVersion, envelope.CanonicalizationVersion);
    }

    [Fact]
    public void Build_ShouldSetEmittedAt_AsRfc3339UtcWithZSuffix()
    {
        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "svc", "1.0", "stage", new List<EvidenceRow>
        {
            Row("OBJ_A", "R_1", EvidenceStatus.Passed),
        });

        Assert.EndsWith("Z", envelope.EmittedAt);
        Assert.True(DateTimeOffset.TryParse(envelope.EmittedAt, null, System.Globalization.DateTimeStyles.RoundtripKind, out _));
    }

    [Theory]
    [InlineData(EvidenceStatus.Error, EvidenceStatus.Failed)]
    [InlineData(EvidenceStatus.Failed, EvidenceStatus.Indeterminate)]
    [InlineData(EvidenceStatus.Indeterminate, EvidenceStatus.Unsupported)]
    [InlineData(EvidenceStatus.Unsupported, EvidenceStatus.Unknown)]
    [InlineData(EvidenceStatus.Unknown, EvidenceStatus.NotEvaluated)]
    [InlineData(EvidenceStatus.NotEvaluated, EvidenceStatus.NoPopulation)]
    [InlineData(EvidenceStatus.NoPopulation, EvidenceStatus.Passed)]
    public void Build_RollupPrecedence_ShouldPreferWorseStatus(EvidenceStatus worse, EvidenceStatus better)
    {
        var rows = new List<EvidenceRow>
        {
            Row("OBJ_A", "R_1", better),
            Row("OBJ_B", "R_2", worse),
        };

        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "svc", "1.0", "stage", rows);

        Assert.Equal(worse, envelope.CanonicalStatus);
    }

    [Fact]
    public void Build_WithEmptyRows_ShouldYieldNotEvaluated()
    {
        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "svc", "1.0", "stage", new List<EvidenceRow>());

        Assert.Equal(EvidenceStatus.NotEvaluated, envelope.CanonicalStatus);
        Assert.Empty(envelope.Rows);
    }

    [Fact]
    public void Build_WithRollUpOverride_ShouldUseOverrideVerbatim()
    {
        var rows = new List<EvidenceRow> { Row("OBJ_A", "R_1", EvidenceStatus.Passed) };

        var envelope = EvidenceEnvelopeFactory.Build(
            "p1", "def-1", "svc", "1.0", "stage", rows, rollUp: EvidenceStatus.NoPopulation);

        Assert.Equal(EvidenceStatus.NoPopulation, envelope.CanonicalStatus);
    }

    [Fact]
    public void SerializedEnvelope_ShouldCarrySchemaFieldNames_AndSnakeCaseStatus()
    {
        var envelope = EvidenceEnvelopeFactory.Build("p1", "def-1", "svc", "1.0", "stage", new List<EvidenceRow>
        {
            Row("OBJ_A", "R_1", EvidenceStatus.NoPopulation),
        });

        var options = new JsonSerializerOptions();
        var json = JsonSerializer.Serialize(envelope, options);
        var node = JsonNode.Parse(json)!;

        var canonical = CanonicalJsonWriter.Canonicalize(node);

        Assert.Contains("\"canonicalStatus\":\"no_population\"", canonical);
        Assert.Contains("\"contractVersion\":\"1.0.0\"", canonical);
        Assert.Contains("\"emittedAt\":", canonical);

        // Ordinal-sorted keys: "canonicalStatus" sorts before "contractVersion" ordinally.
        var canonicalStatusIndex = canonical.IndexOf("\"canonicalStatus\"", StringComparison.Ordinal);
        var contractVersionIndex = canonical.IndexOf("\"contractVersion\"", StringComparison.Ordinal);
        Assert.True(canonicalStatusIndex < contractVersionIndex);
    }

    [Fact]
    public void ToLegacyBoolean_ShouldReturnTrue_OnlyForPassed()
    {
        Assert.True(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Passed));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Failed));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Unknown));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.NotEvaluated));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.NoPopulation));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Unsupported));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Indeterminate));
        Assert.False(EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.Error));
    }
}
