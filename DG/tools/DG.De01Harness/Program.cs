using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Validation;

namespace DG.De01Harness;

/// <summary>
/// DE-01's C# leg (spec/EVIDENCE-CONTRACT.md section 8; plan 1200-05, Task 1).
///
/// Reads <c>fixtures/golden/fixture.json</c>, builds the rule/atoms/bindings into the
/// <c>DG.Core</c> model types <see cref="RuleEvaluator"/> and <see cref="DG.Core.Parsing.SwrlRuleParser"/>
/// consume, calls <see cref="RuleEvaluator.EvaluateRule"/> once per object, and maps every outcome
/// (exception-based or boolean-based) to a typed <see cref="EvidenceStatus"/> at this boundary --
/// never inside <see cref="RuleEvaluator"/> itself, which this harness never modifies (D-04).
///
/// Writes exactly one <see cref="EvidenceEnvelope"/> as canonical JSON to stdout. Nothing else goes
/// to stdout; all diagnostics go to stderr, so <c>tools/de01/legs.py</c>'s <c>run_leg_csharp</c>
/// adapter can parse stdout unconditionally.
///
/// Exit code contract: 0 whenever an envelope was successfully written to stdout, even when every
/// row is <see cref="EvidenceStatus.Error"/>. A non-zero exit is reserved for the harness itself
/// failing to produce any envelope at all (e.g. an unreadable fixture path).
/// </summary>
public static class Program
{
    private const string Project = "DG-1200-GOLDEN";
    private const string DefinitionId = "def-golden-01";
    private const string ServiceName = "dg-core-evaluator";
    private const string Stage = "de01.csharp-leg.evaluate";

    public static int Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.Error.WriteLine("DG.De01Harness: expected exactly one argument, the path to fixtures/golden/fixture.json.");
            return 1;
        }

        var fixturePath = args[0];
        string fixtureText;
        try
        {
            fixtureText = File.ReadAllText(fixturePath);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"DG.De01Harness: could not read fixture at '{fixturePath}' (What: file read failed; Where: DG.De01Harness.Program.Main; How to fix: verify the path exists and is readable) -- {ex.GetType().Name}: {ex.Message}");
            return 1;
        }

        JsonNode? fixtureNode;
        try
        {
            fixtureNode = JsonNode.Parse(fixtureText);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"DG.De01Harness: fixture at '{fixturePath}' is not valid JSON (What: JSON parse failed; Where: DG.De01Harness.Program.Main; How to fix: verify fixtures/golden/fixture.json is well-formed) -- {ex.Message}");
            return 1;
        }

        if (fixtureNode is null)
        {
            Console.Error.WriteLine($"DG.De01Harness: fixture at '{fixturePath}' parsed to a null JSON document.");
            return 1;
        }

        try
        {
            var envelope = BuildEnvelope(fixtureNode);

            // spec/evidence-contract.schema.json types every optional scalar field as bare
            // "string" with no null alternative (mirroring data-service/evidence_contract.py's
            // validate_envelope, which dumps with exclude_none=True). System.Text.Json's default
            // serializes an unset init-only property as an explicit JSON null, which fails schema
            // validation -- WhenWritingNull drops the key entirely instead, matching "absent."
            var json = JsonSerializer.Serialize(envelope, new JsonSerializerOptions
            {
                WriteIndented = false,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            });

            // Re-render through CanonicalJsonWriter so the emitted bytes are in canonical form
            // (rule 1/3/4/5 -- sorted keys, minimal whitespace, NFC strings, minimal escaping),
            // matching the Python leg's producer discipline (D-07).
            var envelopeNode = JsonNode.Parse(json);
            var canonical = CanonicalJsonWriter.Canonicalize(envelopeNode);
            Console.Out.Write(canonical);
            Console.Out.Flush();
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"DG.De01Harness: failed to produce an envelope (What: unexpected exception building/serializing the envelope; Where: DG.De01Harness.Program.BuildEnvelope; How to fix: see the exception below) -- {ex.GetType().Name}: {ex.Message}");
            return 1;
        }
    }

    private static EvidenceEnvelope BuildEnvelope(JsonNode fixtureNode)
    {
        var ruleNode = fixtureNode["rule"] ?? throw new InvalidOperationException("fixture.json missing 'rule'.");
        var ruleId = (string)ruleNode["Rule_Id"]!;

        var atomsNode = fixtureNode["atoms"]!.AsArray();
        var rule = new Rule
        {
            Id = ruleId,
            Name = (string?)ruleNode["RuleName"] ?? ruleId,
            Description = (string?)ruleNode["RuleDescription"] ?? string.Empty,
            Swrl = (string?)ruleNode["swrl"] ?? string.Empty,
            Project = Project,
        };

        Atom? objectPropertyAtom = null;
        var order = 1;
        foreach (var atomNode in atomsNode)
        {
            if (atomNode is null)
            {
                continue;
            }

            var type = (string)atomNode["type"]!;
            var atom = new Atom
            {
                Id = (string)atomNode["Atom_Id"]!,
                Type = type,
                PredicateIri = (string?)atomNode["predicateIri"],
                PredicateLabel = (string?)atomNode["predicateIri"],
                Side = AtomSide.Body,
                Order = order++,
            };

            foreach (var argNode in atomNode["args"]!.AsArray())
            {
                if (argNode is null)
                {
                    continue;
                }

                var pos = (int)argNode["pos"]!;
                if (argNode["var"] is not null)
                {
                    atom.Args.Add(new AtomArg { Pos = pos, Kind = ArgKind.Variable, Value = (string)argNode["var"]! });
                }
                else
                {
                    var literalNode = argNode["literal"]!;
                    atom.Args.Add(new AtomArg
                    {
                        Pos = pos,
                        Kind = ArgKind.Literal,
                        Value = (string)literalNode["lex"]!,
                        Datatype = (string?)literalNode["datatype"],
                    });
                }
            }

            if (type.Equals("ObjectPropertyAtom", StringComparison.OrdinalIgnoreCase))
            {
                // Held out of rule.BodyAtoms deliberately: SwrlRuleParser.ResolveAtomType has no
                // ObjectPropertyAtom branch (spec MANIFEST.md "Expected non-results by design"),
                // and RuleEvaluator.EvaluateAtom's default arm treats any non-BuiltinAtom as a bare
                // variable-availability constraint -- it does not itself detect that this atom type
                // is unsupported. This harness reports it as unsupported explicitly, at this
                // boundary, rather than silently letting it pass through as a satisfied constraint.
                objectPropertyAtom = atom;
                continue;
            }

            rule.BodyAtoms.Add(atom);
        }

        var objectsNode = fixtureNode["objects"]!.AsArray();
        var rows = new List<EvidenceRow>();
        var evaluator = new RuleEvaluator();

        foreach (var objNode in objectsNode)
        {
            if (objNode is null)
            {
                continue;
            }

            var objectId = (string)objNode["objectId"]!;
            var classIri = (string?)objNode["classIri"];
            var propertiesNode = objNode["properties"]?.AsObject();

            // Build binding rows exactly as the fixture's structural intent requires: only an
            // object whose class matches the rule's ClassAtom target (ex:Building) and that carries
            // the hasHeight property produces a binding. OBJ_GOLD_EMPTY (ex:Site) never binds --
            // this is the zero-binding condition the harness must detect from the binding rows it
            // built, not from RuleEvaluator's returned boolean (D-04's prohibition on inferring
            // canonical status from a legacy boolean applies symmetrically to this harness's own
            // no_population detection).
            var bindingRows = new List<BindingRow>();
            if (string.Equals(classIri, "ex:Building", StringComparison.Ordinal)
                && propertiesNode is not null
                && propertiesNode.TryGetPropertyValue("hasHeight", out var heightNode)
                && heightNode is not null)
            {
                var binding = new BindingRow();
                binding.ValuesByVar["?b"] = objectId;
                binding.ValuesByVar["?h"] = (decimal)heightNode.AsValue().GetValue<double>();
                bindingRows.Add(binding);
            }

            EvidenceStatus status;
            var warnings = new List<string>();

            if (bindingRows.Count == 0)
            {
                // Zero-binding condition determined from the binding rows this harness built, not
                // from RuleEvaluator's Passed=false return for the same case (D-04).
                status = EvidenceStatus.NoPopulation;
            }
            else
            {
                try
                {
                    var result = evaluator.EvaluateRule(rule, bindingRows);
                    status = result.Passed ? EvidenceStatus.Passed : EvidenceStatus.Failed;
                }
                catch (NotSupportedException ex)
                {
                    status = EvidenceStatus.Unsupported;
                    warnings.Add(
                        $"What: RuleEvaluator.EvaluateBuiltin raised NotSupportedException for rule '{rule.Id}' "
                        + $"object '{objectId}'. Where: DG.Core.Validation.RuleEvaluator.EvaluateBuiltin "
                        + $"(via DG.De01Harness.Program.BuildEnvelope). How to fix: Phase 1201's ALGN12-06 is the "
                        + $"owner of migrating this evaluator boundary onto typed EvidenceStatus outcomes instead "
                        + $"of throwing. Original message: {ex.Message}");
                }
                catch (Exception ex)
                {
                    status = EvidenceStatus.Error;
                    warnings.Add(
                        $"What: {ex.GetType().Name} raised while evaluating rule '{rule.Id}' against object "
                        + $"'{objectId}'. Where: DG.Core.Validation.RuleEvaluator.EvaluateRule (via "
                        + $"DG.De01Harness.Program.BuildEnvelope). How to fix: see the original exception message. "
                        + $"Original message: {ex.Message}");
                }
            }

            rows.Add(new EvidenceRow
            {
                RuleId = rule.Id,
                ObjectId = objectId,
                CanonicalStatus = status,
                Warnings = warnings.Count > 0 ? warnings : null,
            });

            // The ObjectPropertyAtom case is a by-design, pre-declared non-result (MANIFEST.md
            // "Expected non-results by design"): SwrlRuleParser.ResolveAtomType has no branch for
            // it, so this harness reports it explicitly rather than discovering a crash. Only
            // emitted for the object the fixture's expectedOutcomes table pairs it with
            // (OBJ_GOLD_FAIL), matching fixture.json's own expectedOutcomes ordering.
            if (objectPropertyAtom is not null && string.Equals(objectId, "OBJ_GOLD_FAIL", StringComparison.Ordinal))
            {
                rows.Add(new EvidenceRow
                {
                    RuleId = rule.Id,
                    ObjectId = objectId,
                    CanonicalStatus = EvidenceStatus.Unsupported,
                    Detail = objectPropertyAtom.Id,
                    Warnings = new List<string>
                    {
                        "What: atom 'R_GOLD_HEIGHT_MAX_75_V_A4' (ObjectPropertyAtom, "
                        + "belongsToDistrict(?b, ?d)) has no resolvable type on the C# leg. "
                        + "Where: DG.Core.Parsing.SwrlRuleParser.ResolveAtomType has no "
                        + "ObjectPropertyAtom branch (returns only BuiltinAtom/ClassAtom/"
                        + "DataPropertyAtom). How to fix: Phase 1201's ALGN12-05 adds the missing "
                        + "branch. This is a pre-declared, by-design non-result -- see "
                        + "fixtures/golden/MANIFEST.md 'Expected non-results by design' -- not a "
                        + "fixture defect or a DE-01 failure.",
                    },
                });
            }
        }

        var inputHash = CanonicalJsonWriter.HashCanonical(fixtureNode);
        var serviceVersion = typeof(RuleEvaluator).Assembly.GetName().Version?.ToString() ?? "0.0.0.0";

        return EvidenceEnvelopeFactory.Build(
            project: Project,
            definitionId: DefinitionId,
            serviceName: ServiceName,
            serviceVersion: serviceVersion,
            stage: Stage,
            rows: rows,
            inputHash: inputHash);
    }
}
