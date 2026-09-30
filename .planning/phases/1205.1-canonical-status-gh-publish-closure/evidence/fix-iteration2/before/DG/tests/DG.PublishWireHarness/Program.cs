using System.Net.Http.Json;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using DG.Core.Contracts;
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Validation;
using DG.Grasshopper.Validation;

// No HTTP client is called: emit writes the actual production HTTP body to stdout;
// read consumes persisted UTF-8 bytes on stdin and invokes the real repository reader.
Console.OutputEncoding = new UTF8Encoding(false);
if (args is ["strict"])
{
    var json = await Console.In.ReadToEndAsync();
    Console.Write(JsonSerializer.Serialize(EvidenceEnvelopeReader.IsStrictEnvelope(json)));
    return;
}
if (args is ["read"])
{
    using var input = new MemoryStream();
    await Console.OpenStandardInput().CopyToAsync(input);
    var bytes = input.ToArray();
    var json = Encoding.UTF8.GetString(bytes);
    var reader = typeof(Neo4jValidGraphRepository).GetMethod(
        "BuildPerObjectVerdicts", BindingFlags.NonPublic | BindingFlags.Static)!;
    var result = (PerObjectVerdictResult)reader.Invoke(null, new object?[] { json })!;
    Console.Write(JsonSerializer.Serialize(new
    {
        inputSha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
        envelopePresent = result.EnvelopePresent,
        verdicts = result.Verdicts.Select(v => new
        {
            objectId = v.ObjectId,
            status = EvidenceStatusNames.ToWireName(v.Status),
            duplicate = v.HasDuplicateRuleObjectRows,
        }),
        collisions = result.CollidingRuleObjectPairs,
    }));
    return;
}

// Explicit test-only factory emission; this does not activate the GH v2 writer.
if (args is ["envelope", var version])
{
    var rows = new[]
    {
        new EvidenceRow { RuleId = "R_ROW", ObjectId = "OBJ", CanonicalStatus = EvidenceStatus.Passed },
        new EvidenceRow { RuleId = "R_ROW", ObjectId = "OBJ", CanonicalStatus = EvidenceStatus.Failed,
            Detail = "duplicate failure", Warnings = new List<string> { "row-warning" } },
        new EvidenceRow { RuleId = "r_row", ObjectId = "obj", CanonicalStatus = EvidenceStatus.Passed },
    };
    var serializerOptions = new JsonSerializerOptions
    {
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };
    var envelopeJson = version switch
    {
        "1.0.0" => JsonSerializer.Serialize(EvidenceEnvelopeFactory.Build("p", "d", "csharp", "1", "test", rows), serializerOptions),
        "2.0.0" => EvidenceEnvelopeReader.Serialize(EvidenceEnvelopeFactory.BuildWithRuleResults(
            "p", "d", "csharp", "1", "test", rows, new[]
            {
                new EvidenceRuleResult { RuleId = "R_ROW", CanonicalStatus = EvidenceStatus.Failed, Warnings = new() },
                new EvidenceRuleResult { RuleId = "R_EMPTY_B", CanonicalStatus = EvidenceStatus.NotEvaluated,
                    Warnings = new List<string> { "not-run" }, Detail = "not evaluated" },
                new EvidenceRuleResult { RuleId = "R_EMPTY_A", CanonicalStatus = EvidenceStatus.NoPopulation, Warnings = new() },
            })),
        _ => throw new ArgumentException("No factory for version " + version),
    };
    Console.Write(envelopeJson);
    return;
}

// Core-only diagnostic inspection retained independently of the wire tests.
if (args is ["core-diagnostics"])
{
    var diagnosticRule = new Rule { Id = "R_DIAG" };
    diagnosticRule.BodyAtoms.Add(new Atom { Type = "ObjectPropertyAtom", PredicateLabel = "belongsTo" });
    var diagnosticBinding = Binding("OBJ_DIAG", 60m);
    var genuine = new RuleEvaluator().EvaluateRule(diagnosticRule, new[] { diagnosticBinding });
    var legacyRule = new Rule { Id = "R_LEGACY" };
    var missingRule = new Rule { Id = "R_MISSING" };
    var diagnosticPackage = ValidationPublishPackageBuilder.Build(
        new[] { diagnosticRule, legacyRule, missingRule },
        new[] { genuine, new RuleEvaluationResult { RuleId = legacyRule.Id, Passed = true } },
        new[] { diagnosticBinding });
    if (string.IsNullOrWhiteSpace(genuine.Message) || string.IsNullOrWhiteSpace(genuine.BindingResults![0].Detail))
        throw new InvalidOperationException("Genuine diagnostic case emitted no details.");
    var entity = diagnosticPackage.Entities.Single();
    if (entity.CanonicalDetails[diagnosticRule.Id] != genuine.BindingResults[0].Detail
        || diagnosticPackage.RuleResults[0].Detail != genuine.Message
        || !entity.CanonicalWarnings[legacyRule.Id].Contains("typed_binding_outcome_unavailable")
        || !diagnosticPackage.RuleResults[1].Warnings.Contains("typed_binding_outcome_unavailable")
        || diagnosticPackage.RuleResults[1].Status != EvidenceStatus.Unknown
        || entity.CanonicalStatuses[missingRule.Id] != EvidenceStatus.NotEvaluated)
        throw new InvalidOperationException("Core diagnostics or exact missing-result association lost.");
    Console.Write(JsonSerializer.Serialize(diagnosticPackage));
    return;
}

if (args is not [var mode, var scenario] || (mode != "emit" && mode != "core"))
    throw new ArgumentException("Usage: emit <scenario> | core <scenario> | read");

var rule = new Rule { Id = "R_WIRE", Project = "P_WIRE" };
var rules = new List<Rule> { rule };
BindingRow[] bindings;
switch (scenario)
{
    case "zero_rows":
        rules.Add(new Rule { Id = "R_EMPTY_B", Project = "P_WIRE" });
        rules.Add(new Rule { Id = "R_MISSING", Project = "P_WIRE" });
        bindings = Array.Empty<BindingRow>();
        break;
    case "supported":
    case "mixed_shortcircuit":
    case "mixed_zero_rows":
    case "missing_association":
    case "repeated_refs":
        var comparison = new Atom { Type = "BuiltinAtom", PredicateLabel = "swrlb:greaterThan" };
        comparison.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" });
        comparison.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75", Datatype = "xsd:integer" });
        rule.BodyAtoms.Add(comparison);
        bindings = new[] { Binding("OBJ_PASS", 60m), Binding("OBJ_FAIL", 80m) };
        if (scenario == "mixed_shortcircuit")
            rule.BodyAtoms.Add(new Atom { Type = "ObjectPropertyAtom", PredicateLabel = "belongsTo" });
        if (scenario == "repeated_refs")
        {
            var first = Binding("OBJ_SHARED", 60m);
            first.ElementRefsByVar["?alias"] = new ElementRef { DgEntityId = "OBJ_SHARED" };
            first.ElementRefsByVar["?other"] = new ElementRef { DgEntityId = "OBJ_A" };
            bindings = new[] { first, first, Binding("OBJ_SHARED", 80m), Binding("OBJ_B", 60m) };
        }
        break;
    case "unsupported":
        rule.BodyAtoms.Add(new Atom { Type = "ObjectPropertyAtom", PredicateLabel = "belongsTo" });
        bindings = new[] { Binding("OBJ_UNSUPPORTED", 60m) };
        break;
    case "diagnostics":
    case "unknown":
        var missingVariable = new Atom { Type = "ClassAtom" };
        missingVariable.Args.Add(new AtomArg { Kind = ArgKind.Variable, Value = "?missing" });
        rule.BodyAtoms.Add(missingVariable);
        if (scenario == "diagnostics") rules.Add(new Rule { Id = "R_LEGACY", Project = "P_WIRE" });
        bindings = new[] { Binding(scenario == "diagnostics" ? "OBJ_DIAG" : "OBJ_UNKNOWN", 60m) };
        break;
    case "error":
        var invalidLiteral = new Atom { Type = "BuiltinAtom", PredicateLabel = "swrlb:greaterThan" };
        invalidLiteral.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" });
        invalidLiteral.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "not-an-integer", Datatype = "xsd:integer" });
        rule.BodyAtoms.Add(invalidLiteral);
        bindings = new[] { Binding("OBJ_ERROR", 60m) };
        break;
    case "missing_result":
    case "legacy_only":
    case "empty_typed":
    case "no_refs":
    case "contract_injected_indeterminate":
        rule.BodyAtoms.Add(new Atom { Type = "ClassAtom" });
        bindings = new[] { Binding(scenario == "missing_result" ? "OBJ_MISSING" :
            scenario == "contract_injected_indeterminate" ? "OBJ_INJECTED" : "OBJ_LEGACY", 60m) };
        if (scenario == "no_refs") bindings[0].ElementRefsByVar.Clear();
        break;
    default:
        throw new ArgumentException($"Unknown scenario: {scenario}");
}

var evaluation = new RuleEvaluator().EvaluateRule(rule, bindings);
if (scenario == "unsupported" && evaluation.Status != EvidenceStatus.Unsupported)
    throw new InvalidOperationException("Unsupported fixture did not reach evaluator Unsupported.");
var evaluations = new List<RuleEvaluationResult> { evaluation };
if (scenario == "zero_rows") evaluations.Add(new RuleEvaluator().EvaluateRule(rules[1], bindings));
if (scenario == "diagnostics") evaluations.Add(new RuleEvaluationResult { RuleId = "R_LEGACY", Passed = true });
if (scenario == "missing_result") evaluations.Clear();
if (scenario is "legacy_only" or "empty_typed")
    evaluations[0] = new RuleEvaluationResult { RuleId = rule.Id, Passed = true,
        BindingResults = scenario == "empty_typed" ? Array.Empty<BindingEvaluationResult>() : null };
if (scenario == "missing_association")
    evaluations[0] = new RuleEvaluationResult { RuleId = rule.Id, Passed = true,
        BindingResults = new[] { evaluation.BindingResults![0] } };
if (scenario == "contract_injected_indeterminate")
    // Contract-only typed injection. The evaluator has no natural Indeterminate branch.
    evaluations[0] = new RuleEvaluationResult { RuleId = rule.Id, Passed = false,
        Status = EvidenceStatus.Indeterminate,
        BindingResults = new[] { new BindingEvaluationResult(bindings[0], EvidenceStatus.Indeterminate, null) } };
var package = ValidationPublishPackageBuilder.Build(rules, evaluations, bindings);
if (scenario == "mixed_zero_rows")
{
    // Build's common-population API cannot evaluate different rule populations in
    // one call. Compose genuine empty-population packages, not invented outcomes.
    var emptyRules = new[] { new Rule { Id = "R_EMPTY_A", Project = "P_WIRE" },
        new Rule { Id = "R_EMPTY_B", Project = "P_WIRE" } };
    var empty = ValidationPublishPackageBuilder.Build(emptyRules,
        new RuleEvaluator().EvaluateRules(emptyRules, Array.Empty<BindingRow>()), Array.Empty<BindingRow>());
    package.Rules.AddRange(empty.Rules);
    package.RuleResults.AddRange(empty.RuleResults);
}
if (mode == "core")
{
    Console.Write(JsonSerializer.Serialize(package));
    return;
}
var producer = typeof(ValidationPublishClient);
var request = (ValidationPublishRequest)producer.GetMethod(
    "BuildRequest", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, new object?[] { package, null })!;
// Same explicit post-BuildRequest assignment used by Publish; test-only values
// deliberately do not derive from canonical booleans.
request.ValidStatus = new List<bool> { true, false, true };
var options = (JsonSerializerOptions)producer.GetField(
    "JsonOptions", BindingFlags.NonPublic | BindingFlags.Static)!.GetValue(null)!;
using var content = JsonContent.Create(request, options: options);
await Console.OpenStandardOutput().WriteAsync(await content.ReadAsByteArrayAsync());

static BindingRow Binding(string objectId, decimal height)
{
    var binding = new BindingRow();
    binding.ValuesByVar["?h"] = height;
    binding.ElementRefsByVar["?b"] = new ElementRef { DgEntityId = objectId };
    return binding;
}

namespace DG.Grasshopper.Validation
{
    // Only the Rhino geometry seam is substituted. Never pretend to serialize geometry.
    internal static class ValidationGeometryPayloadSerializer
    {
        public static ValidationGeometryPayload? Serialize(object? geometry) => geometry is null
            ? null : throw new InvalidOperationException("Wire harness supports null geometry only.");
    }
}
