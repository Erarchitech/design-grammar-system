using System;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using DG.Core.Contracts;

namespace DG.Tests;

public sealed class CanonicalJsonWriterTests
{
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

        throw new DirectoryNotFoundException($"CanonicalJsonWriterTests.FindRepoRoot: could not locate repo root walking up from {AppContext.BaseDirectory}.");
    }

    private static string GoldenVectorsPathFromTestOutput()
    {
        return Path.Combine(AppContext.BaseDirectory, "Fixtures", "golden", "canonical-vectors.json");
    }

    [Fact]
    public void HashScalarTuple_ShouldMatchShippedDgIdVector()
    {
        var digest = CanonicalJsonWriter.HashScalarTuple("p1", "frame.gh", "cg:1:proc:11_Proc");

        Assert.StartsWith("BC8E62EE137E2B56", digest);
        Assert.Equal(64, digest.Length);
    }

    [Fact]
    public void HashScalarTuple_ShouldThrow_ForEmptyPart()
    {
        Assert.Throws<ArgumentException>(() => CanonicalJsonWriter.HashScalarTuple("p1", "", "cg:1"));
    }

    [Fact]
    public void Canonicalize_ShouldSortObjectKeys_Ordinally()
    {
        var node = JsonNode.Parse("{\"b\":1,\"a\":2}");

        var canonical = CanonicalJsonWriter.Canonicalize(node);

        Assert.Equal("{\"a\":2,\"b\":1}", canonical);
    }

    [Fact]
    public void Canonicalize_ShouldNormalizeString_ToNfcForm()
    {
        // "Café" authored in NFD (decomposed): e + combining acute accent (U+0301).
        var nfd = "Café";
        var obj = new JsonObject { ["note"] = nfd };

        var canonical = CanonicalJsonWriter.Canonicalize(obj);

        Assert.Equal("{\"note\":\"Café\"}", canonical);
    }

    [Fact]
    public void Canonicalize_ShouldLeaveNonAsciiUnescaped()
    {
        var obj = new JsonObject { ["label"] = "Façade" };

        var canonical = CanonicalJsonWriter.Canonicalize(obj);

        Assert.Equal("{\"label\":\"Façade\"}", canonical);
    }

    [Fact]
    public void Canonicalize_ShouldRenderDecimal_AsFixedPoint()
    {
        var obj = new JsonObject { ["height"] = 82.5m };

        var canonical = CanonicalJsonWriter.Canonicalize(obj);

        Assert.Equal("{\"height\":82.5}", canonical);
    }

    [Fact]
    public void Canonicalize_ShouldPreserveTrailingZeroScale()
    {
        var obj = new JsonObject { ["amount"] = 100.00m, ["ratio"] = 2.50m };

        var canonical = CanonicalJsonWriter.Canonicalize(obj);

        Assert.Equal("{\"amount\":100.00,\"ratio\":2.50}", canonical);
    }

    [Fact]
    public void Canonicalize_ShouldRenderIntegralDecimal_WithNoDecimalPoint()
    {
        var scaleZero = new JsonObject { ["count"] = 3m };
        var aboveOldCutoff = new JsonObject { ["count"] = 2000000000000000m };

        var scaleZeroCanonical = CanonicalJsonWriter.Canonicalize(scaleZero);
        var aboveOldCutoffCanonical = CanonicalJsonWriter.Canonicalize(aboveOldCutoff);

        Assert.Equal("{\"count\":3}", scaleZeroCanonical);
        Assert.Equal("{\"count\":2000000000000000}", aboveOldCutoffCanonical);
    }

    [Fact]
    public void Canonicalize_ShouldRejectDouble()
    {
        var obj = new JsonObject { ["height"] = 82.5d };

        Assert.Throws<NotSupportedException>(() => CanonicalJsonWriter.Canonicalize(obj));
    }

    [Fact]
    public void Canonicalize_ShouldThrow_ForNaN()
    {
        Assert.Throws<NotSupportedException>(() => CanonicalJsonWriter.Canonicalize(JsonValue.Create(double.NaN)));
    }

    [Fact]
    public void Canonicalize_ShouldThrow_ForInfinity()
    {
        Assert.Throws<NotSupportedException>(() => CanonicalJsonWriter.Canonicalize(JsonValue.Create(double.PositiveInfinity)));
    }

    [Fact]
    public void CanonicalJson_ShouldBeDeterministic_AcrossGoldenVectors()
    {
        var path = GoldenVectorsPathFromTestOutput();
        Assert.True(File.Exists(path), $"Expected golden vectors file copied to test output at {path}.");

        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var vectors = doc.RootElement.GetProperty("vectors");

        var canonicalJsonVectorCount = 0;
        var sawTrailingZeroDecimal = false;

        foreach (var vector in vectors.EnumerateArray())
        {
            if (vector.GetProperty("kind").GetString() != "canonicalJson")
            {
                continue;
            }

            canonicalJsonVectorCount++;

            var expectedCanonical = vector.GetProperty("canonical").GetString();
            var expectedDigest = vector.GetProperty("sha256Upper").GetString();

            var valueNode = ParseAsDecimalPreservingNode(vector.GetProperty("value"));

            var actualCanonical = CanonicalJsonWriter.Canonicalize(valueNode);
            var actualDigest = CanonicalJsonWriter.HashCanonical(valueNode);

            Assert.Equal(expectedCanonical, actualCanonical);
            Assert.Equal(expectedDigest, actualDigest);

            if (expectedCanonical is not null && Regex.IsMatch(expectedCanonical, @":-?\d+\.\d*0[,}]"))
            {
                sawTrailingZeroDecimal = true;
            }
        }

        Assert.True(canonicalJsonVectorCount > 0, "Expected at least one canonicalJson vector in the golden fixture — the test cannot pass vacuously.");
        Assert.True(sawTrailingZeroDecimal, "Expected at least one canonicalJson vector's canonical string to carry a trailing-zero decimal (CR-01 regression coverage) — the test would silently pass if that vector were removed.");
    }

    [Fact]
    public void ScalarTupleHash_ShouldMatchShippedDgIdVector()
    {
        var path = GoldenVectorsPathFromTestOutput();
        Assert.True(File.Exists(path), $"Expected golden vectors file copied to test output at {path}.");

        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var vectors = doc.RootElement.GetProperty("vectors");

        var scalarTupleVectorCount = 0;

        foreach (var vector in vectors.EnumerateArray())
        {
            if (vector.GetProperty("kind").GetString() != "scalarTuple")
            {
                continue;
            }

            scalarTupleVectorCount++;

            var parts = vector.GetProperty("parts").EnumerateArray();
            var partsArray = System.Linq.Enumerable.ToArray(
                System.Linq.Enumerable.Select(vector.GetProperty("parts").EnumerateArray(), p => p.GetString()!));

            var expectedDigest = vector.GetProperty("sha256Upper").GetString();
            var actualDigest = CanonicalJsonWriter.HashScalarTuple(partsArray);

            Assert.Equal(expectedDigest, actualDigest);
        }

        Assert.True(scalarTupleVectorCount > 0, "Expected at least one scalarTuple vector in the golden fixture.");
    }

    /// <summary>
    /// Parses a <see cref="JsonElement"/> tree into a <see cref="JsonNode"/> tree where every JSON
    /// number becomes a <see cref="decimal"/> (never a double), matching how a real producer must
    /// construct its canonicalization input per rule 2. The golden vectors file itself is only a
    /// literal-assertion source (per its own _comment), so this reparse step is test-harness
    /// plumbing, not a second implementation of the canonicalization rules.
    /// </summary>
    private static JsonNode? ParseAsDecimalPreservingNode(JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                var obj = new JsonObject();
                foreach (var prop in element.EnumerateObject())
                {
                    obj[prop.Name] = ParseAsDecimalPreservingNode(prop.Value);
                }

                return obj;
            case JsonValueKind.Array:
                var arr = new JsonArray();
                foreach (var item in element.EnumerateArray())
                {
                    arr.Add(ParseAsDecimalPreservingNode(item));
                }

                return arr;
            case JsonValueKind.String:
                return JsonValue.Create(element.GetString());
            case JsonValueKind.Number:
                return JsonValue.Create(element.GetDecimal());
            case JsonValueKind.True:
                return JsonValue.Create(true);
            case JsonValueKind.False:
                return JsonValue.Create(false);
            case JsonValueKind.Null:
                return null;
            default:
                throw new NotSupportedException($"Unsupported JsonValueKind {element.ValueKind} in golden vector fixture.");
        }
    }
}
