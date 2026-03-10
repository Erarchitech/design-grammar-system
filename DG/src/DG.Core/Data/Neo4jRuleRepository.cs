using System.Text.RegularExpressions;
using DG.Core.Models;
using DG.Core.Parsing;
using Neo4j.Driver;

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

    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    private const string RulesQuery = """
        MATCH (r:Rule {graph:'Metagraph', project:$project})
        RETURN
            r.Rule_Id AS id,
            coalesce(r.title, r.name, r.Rule_Id) AS name,
            coalesce(r.description, '') AS description,
            coalesce(r.kind, 'violation') AS kind,
            coalesce(r.text, '') AS text,
            coalesce(r.swrl, r.text, '') AS swrl,
            coalesce(r.project, $project) AS project,
            coalesce(r.graph, 'Metagraph') AS graph
        ORDER BY id
        """;

    private const string AtomsQuery = """
        MATCH (r:Rule {graph:'Metagraph', project:$project})-[rel:HAS_BODY|HAS_HEAD]->(a:Atom {graph:'Metagraph', project:$project})
        OPTIONAL MATCH (a)-[:REFERS_TO]->(p)
        OPTIONAL MATCH (a)-[arg:ARG]->(av)
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

    public async Task<IReadOnlyList<Rule>> GetRulesAsync(ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));

        var rules = await LoadRulesAsync(session, connection.Project, cancellationToken);
        if (rules.Count == 0)
        {
            return rules.Values.ToList();
        }

        await LoadAtomsAsync(session, connection.Project, rules, cancellationToken);
        PopulateVariables(rules.Values);
        return rules.Values.ToList();
    }

    private static async Task<Dictionary<string, Rule>> LoadRulesAsync(
        IAsyncSession session,
        string project,
        CancellationToken cancellationToken)
    {
        var cursor = await session
            .RunAsync(RulesQuery, new { project })
            .WaitAsync(QueryTimeout, cancellationToken);
        var rules = new Dictionary<string, Rule>(StringComparer.Ordinal);

        await cursor
            .ForEachAsync(record =>
            {
                var id = record["id"].As<string>();
                rules[id] = new Rule
                {
                    Id = id,
                    Name = record["name"].As<string>(),
                    Description = CleanDescription(record["description"].As<string>()),
                    Kind = record["kind"].As<string>(),
                    Text = record["text"].As<string>(),
                    Swrl = record["swrl"].As<string>(),
                    Project = record["project"].As<string>(),
                    Graph = record["graph"].As<string>(),
                };
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return rules;
    }

    private static async Task LoadAtomsAsync(
        IAsyncSession session,
        string project,
        IDictionary<string, Rule> rules,
        CancellationToken cancellationToken)
    {
        var cursor = await session
            .RunAsync(AtomsQuery, new { project })
            .WaitAsync(QueryTimeout, cancellationToken);
        var atomCache = new Dictionary<string, Atom>(StringComparer.Ordinal);

        await cursor
            .ForEachAsync(record =>
            {
                var ruleId = record["ruleId"].As<string>();
                if (!rules.TryGetValue(ruleId, out var rule))
                {
                    return;
                }

                var atomId = record["atomId"].As<string>();
                var relationType = record["relationType"].As<string>();
                var side = relationType.Equals("HAS_HEAD", StringComparison.OrdinalIgnoreCase) ? AtomSide.Head : AtomSide.Body;
                var cacheKey = $"{ruleId}|{atomId}";

                if (!atomCache.TryGetValue(cacheKey, out var atom))
                {
                    atom = new Atom
                    {
                        Id = atomId,
                        Type = record["atomType"].As<string>(),
                        PredicateIri = record["predicateIri"].As<string?>(),
                        PredicateLabel = record["predicateLabel"].As<string?>(),
                        Side = side,
                        Order = record["atomOrder"].As<int>(),
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

                var labels = record["argLabels"].As<List<string>>();
                if (labels.Count == 0)
                {
                    return;
                }

                var isVariable = labels.Contains("Var", StringComparer.OrdinalIgnoreCase);
                var argValue = isVariable
                    ? record["varName"].As<string?>()
                    : record["litLex"].As<string?>();

                if (string.IsNullOrWhiteSpace(argValue))
                {
                    return;
                }

                var argPos = record["argPos"].As<int>();
                if (argPos <= 0 || atom.Args.Any(arg => arg.Pos == argPos))
                {
                    return;
                }

                atom.Args.Add(new AtomArg
                {
                    Pos = argPos,
                    Kind = isVariable ? ArgKind.Variable : ArgKind.Literal,
                    Value = argValue,
                    Datatype = isVariable ? null : record["litDatatype"].As<string?>(),
                });
            })
            .WaitAsync(QueryTimeout, cancellationToken);

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

            foreach (var variableName in names.OrderBy(name => name, StringComparer.Ordinal))
            {
                rule.Variables.Add(new Variable { Name = variableName });
            }
        }
    }

}
