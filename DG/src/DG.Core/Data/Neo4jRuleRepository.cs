using System.Text.RegularExpressions;
using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Data;

public sealed class Neo4jRuleRepository : IRuleRepository
{
    private static readonly Regex EditPrefixPattern = new(
        @"^edit\s+Rule_Id:\s*\S+\s*[\u2014—-]\s*",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static string CleanDescription(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;
        return EditPrefixPattern.Replace(raw, string.Empty).Trim();
    }

    // WHERE NOT EXISTS SUPERSEDED_BY (debug session rule-ingest-no-conflict-check,
    // 2026-09-19): a Replace/Update action from the new ingest conflict-check gate
    // records provenance via an old-Rule -[:SUPERSEDED_BY]-> new-Rule edge instead
    // of deleting the old Rule outright (paper [P129]/[P139] -- versioned
    // proposals, provenance recording, never silent overwrite). The SWRL
    // VALIDATOR's corpus MUST exclude a superseded rule, or it keeps firing
    // alongside its replacement -- the exact bug the conflict-check gate exists to
    // close, reproduced in a new form if this filter is ever removed.
    private const string RulesQuery = """
        MATCH (r:Rule {graph:'Metagraph', project:$project})
        WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
        RETURN
            r.Rule_Id AS id,
            coalesce(r.RuleName, r.title, r.name, r.Rule_Id) AS name,
            coalesce(r.RuleDescription, r.description, '') AS description,
            coalesce(r.kind, 'violation') AS kind,
            coalesce(r.text, '') AS text,
            coalesce(r.SWRL, r.swrl, r.text, '') AS swrl,
            coalesce(r.project, $project) AS project,
            coalesce(r.graph, 'Metagraph') AS graph
        ORDER BY id
        """;

    private const string AtomsQuery = """
        MATCH (r:Rule {graph:'Metagraph', project:$project})-[rel:HAS_BODY|HAS_HEAD]->(a:Atom {graph:'Metagraph', project:$project})
        OPTIONAL MATCH (a)-[:REFERS_TO]->(p)
        OPTIONAL MATCH (a)-[arg:ARG]->(av)
        WHERE av IS NULL OR av.project IS NULL OR av.project = $project
        RETURN
            r.Rule_Id AS ruleId,
            type(rel) AS relationType,
            coalesce(rel.`order`, 0) AS atomOrder,
            a.Atom_Id AS atomId,
            coalesce(a.type, '') AS atomType,
            coalesce(p.iri, a.iri) AS predicateIri,
            coalesce(p.label, p.SWRL_label, a.SWRL_label) AS predicateLabel,
            coalesce(arg.`pos`, 0) AS argPos,
            labels(av) AS argLabels,
            av.name AS varName,
            av.lex AS litLex,
            av.datatype AS litDatatype
        ORDER BY ruleId, relationType, atomOrder, argPos
        """;

    private const string ObjectsQuery = """
        MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class)
        RETURN DISTINCT c.iri AS iri, c.label AS label
        ORDER BY c.label
        """;

    public async Task<IReadOnlyList<Rule>> GetRulesAsync(ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        using var session = GraphQuerySession.Open(connection);

        var rules = await LoadRulesAsync(session, cancellationToken);
        if (rules.Count == 0)
        {
            return rules.Values.ToList();
        }

        await LoadAtomsAsync(session, rules, cancellationToken);
        PopulateVariables(rules.Values);
        return rules.Values.ToList();
    }

    public async Task<IReadOnlyList<OntologyClass>> GetObjectsAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        using var session = GraphQuerySession.Open(connection);

        var rows = await session.QueryAsync("objects", ObjectsQuery, null, cancellationToken);
        return rows
            .Select(record => new OntologyClass { Iri = record.GetString("iri")!, Label = record.GetString("label")! })
            .ToList();
    }

    private static async Task<Dictionary<string, Rule>> LoadRulesAsync(
        IGraphQuerySession session,
        CancellationToken cancellationToken)
    {
        var records = await session.QueryAsync("rules", RulesQuery, null, cancellationToken);
        var rules = new Dictionary<string, Rule>(StringComparer.Ordinal);

        foreach (var record in records)
        {
            var id = record.GetString("id")!;
            rules[id] = new Rule
            {
                Id = id,
                Name = record.GetString("name")!,
                Description = CleanDescription(record.GetString("description")!),
                Kind = record.GetString("kind")!,
                Text = record.GetString("text")!,
                Swrl = record.GetString("swrl")!,
                Project = record.GetString("project")!,
                Graph = record.GetString("graph")!,
            };
        }

        return rules;
    }

    private static async Task LoadAtomsAsync(
        IGraphQuerySession session,
        IDictionary<string, Rule> rules,
        CancellationToken cancellationToken)
    {
        var records = await session.QueryAsync("atoms", AtomsQuery, null, cancellationToken);
        var atomCache = new Dictionary<string, Atom>(StringComparer.Ordinal);

        foreach (var record in records)
        {
            var ruleId = record.GetString("ruleId")!;
            if (!rules.TryGetValue(ruleId, out var rule))
            {
                continue;
            }

            var atomId = record.GetString("atomId")!;
            var relationType = record.GetString("relationType")!;
            var side = relationType.Equals("HAS_HEAD", StringComparison.OrdinalIgnoreCase) ? AtomSide.Head : AtomSide.Body;
            var cacheKey = $"{ruleId}|{atomId}";

            if (!atomCache.TryGetValue(cacheKey, out var atom))
            {
                atom = new Atom
                {
                    Id = atomId,
                    Type = record.GetString("atomType")!,
                    PredicateIri = record.GetString("predicateIri"),
                    PredicateLabel = record.GetString("predicateLabel"),
                    Side = side,
                    Order = record.GetInt("atomOrder"),
                };
                atomCache[cacheKey] = atom;

                if (side == AtomSide.Body)
                {
                    rule.BodyAtoms.Add(atom);
                }
                else
                {
                    rule.HeadAtoms.Add(atom);
                }
            }

            var labels = record.GetStringList("argLabels");
            if (labels.Count == 0)
            {
                continue;
            }

            var isVariable = labels.Contains("Var", StringComparer.OrdinalIgnoreCase);
            var isLiteral = labels.Contains("Literal", StringComparer.OrdinalIgnoreCase);
            if (isVariable == isLiteral)
            {
                // Both or neither — malformed ARG target, skip rather than silently misclassify.
                continue;
            }

            var argValue = isVariable
                ? record.GetString("varName")
                : record.GetString("litLex");

            if (string.IsNullOrWhiteSpace(argValue))
            {
                continue;
            }

            var argPos = record.GetInt("argPos");
            if (argPos <= 0 || atom.Args.Any(arg => arg.Pos == argPos))
            {
                continue;
            }

            atom.Args.Add(new AtomArg
            {
                Pos = argPos,
                Kind = isVariable ? ArgKind.Variable : ArgKind.Literal,
                Value = argValue,
                Datatype = isVariable ? null : record.GetString("litDatatype"),
            });
        }

        foreach (var rule in rules.Values)
        {
            SortAtoms(rule.BodyAtoms);
            SortAtoms(rule.HeadAtoms);
        }
    }

    private static void SortAtoms(ICollection<Atom> atoms)
    {
        var ordered = atoms
            .OrderBy(atom => atom.Order)
            .ThenBy(atom => atom.Id, StringComparer.Ordinal)
            .ToList();

        atoms.Clear();
        foreach (var atom in ordered)
        {
            var orderedArgs = atom.Args.OrderBy(arg => arg.Pos).ToList();
            atom.Args.Clear();
            foreach (var arg in orderedArgs)
            {
                atom.Args.Add(arg);
            }

            atoms.Add(atom);
        }
    }

    /// <summary>
    /// Test-only entry point exposing <see cref="PopulateVariables"/> for unit testing without
    /// a live Neo4j connection. Not part of <see cref="IRuleRepository"/>'s public contract.
    /// </summary>
    internal static void PopulateVariablesForTesting(IEnumerable<Rule> rules) => PopulateVariables(rules);

    private static void PopulateVariables(IEnumerable<Rule> rules)
    {
        foreach (var rule in rules)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var name in rule.BodyAtoms
                         .Concat(rule.HeadAtoms)
                         .SelectMany(atom => atom.Args)
                         .Where(arg => arg.Kind == ArgKind.Variable)
                         .Select(arg => arg.Value))
            {
                names.Add(name);
            }

            if (!string.IsNullOrWhiteSpace(rule.Swrl))
            {
                try
                {
                    var parsed = SwrlRuleParser.Parse(rule.Swrl);
                    foreach (var variable in parsed.Variables)
                    {
                        names.Add(variable.Name);
                    }

                    if (rule.BodyAtoms.Count == 0)
                    {
                        foreach (var atom in parsed.BodyAtoms)
                        {
                            rule.BodyAtoms.Add(atom);
                        }
                    }

                    if (rule.HeadAtoms.Count == 0)
                    {
                        foreach (var atom in parsed.HeadAtoms)
                        {
                            rule.HeadAtoms.Add(atom);
                        }
                    }
                }
                catch (Exception ex) when (ex is ArgumentException or FormatException)
                {
                    // Malformed SWRL text (e.g. legacy/manually-edited rules) must not abort
                    // loading the rest of the project's rules. Continue with whatever atoms
                    // and variable names were already loaded from the graph for this rule.
                    Console.Error.WriteLine(
                        $"PopulateVariables: failed to parse SWRL for rule '{rule.Id}': {ex.Message}");
                }
            }

            foreach (var variableName in names.OrderBy(name => name, StringComparer.Ordinal))
            {
                rule.Variables.Add(new Variable { Name = variableName, Kind = VariableTypeInferrer.Infer(rule, variableName) });
            }
        }
    }

}
