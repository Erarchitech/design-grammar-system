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
}
