using DG.Core.Contracts;
using DG.Core.Models;

namespace DG.Core.Validation;

public static class ValidationPublishPackageBuilder
{
    private const string UnavailableWarning = "typed_binding_outcome_unavailable";
    private const string InconsistentWarning = "typed_binding_outcome_inconsistent";
    private const string UnavailableDetail = "Typed binding outcomes are unavailable for the supplied binding population; canonical success cannot be inferred from legacy fields.";
    public static ValidationPublishPackage Build(
        IReadOnlyList<Rule> rules,
        IReadOnlyList<RuleEvaluationResult> results,
        IReadOnlyList<BindingRow> bindings)
    {
        if (rules.Count == 0)
        {
            throw new InvalidOperationException("At least one rule is required to publish validation results.");
        }

        var project = ResolveProject(rules);
        var resultById = results.ToDictionary(result => result.RuleId, StringComparer.Ordinal);
        var entityById = new Dictionary<string, ValidationPublishEntity>(StringComparer.Ordinal);
        var missingRules = new List<Rule>();
        var package = new ValidationPublishPackage
        {
            Project = project,
        };

        foreach (var rule in rules)
        {
            package.Rules.Add(new ValidationPublishRule
            {
                RuleId = rule.Id,
                RuleName = rule.Name,
                RuleDescription = rule.Description,
            });

            if (!resultById.TryGetValue(rule.Id, out var result))
            {
                // Phase 1201 plan 02: `not_evaluated` is "the rule was in scope but no evaluation
                // was ever attempted or no result was produced" (spec/EVIDENCE-CONTRACT.md) — this
                // TryGetValue miss is exactly that branch, and it is distinct from `unknown`, where
                // evaluation happened and could not resolve. Without a typed status here, a rule
                // that was never evaluated is indistinguishable at the publish boundary from an
                // evaluated violation (Passed=false either way) — T-1201-04's repudiation risk.
                package.RuleResults.Add(new ValidationPublishRuleResult
                {
                    RuleId = rule.Id,
                    Passed = false,
                    Status = EvidenceStatus.NotEvaluated,
                });
                missingRules.Add(rule);
                continue;
            }

            var failingBindings = new HashSet<BindingRow>(result.FailingBindings);
            var statusByEntity = new Dictionary<string, bool>(StringComparer.Ordinal);
            var refByEntity = new Dictionary<string, ElementRef>(StringComparer.Ordinal);
            var bindingByEntity = new Dictionary<string, BindingRow>(StringComparer.Ordinal);
            var canonicalByEntity = new Dictionary<string, List<EvidenceStatus>>(StringComparer.Ordinal);
            var warningsByEntity = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            var detailsByEntity = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            var canonicalBindings = new HashSet<BindingRow>(ReferenceEqualityComparer.Instance);
            var outcomesByBinding = new Dictionary<BindingRow, List<BindingEvaluationResult>>(ReferenceEqualityComparer.Instance);
            foreach (var outcome in result.BindingResults ?? Array.Empty<BindingEvaluationResult>())
            {
                if (!outcomesByBinding.TryGetValue(outcome.Binding, out var statuses))
                {
                    statuses = new List<BindingEvaluationResult>();
                    outcomesByBinding.Add(outcome.Binding, statuses);
                }
                statuses.Add(outcome);
            }

            var population = new HashSet<BindingRow>(bindings, ReferenceEqualityComparer.Instance);
            var unavailable = result.BindingResults is null || population.Any(b => !outcomesByBinding.ContainsKey(b));
            var inconsistent = outcomesByBinding.Any(p => !population.Contains(p.Key) || p.Value.Count > 1);

            foreach (var binding in bindings)
            {
                var elementRefs = ExtractElementRefs(binding);
                if (elementRefs.Count == 0)
                {
                    continue;
                }

                var isFailingBinding = failingBindings.Contains(binding);
                var firstCanonicalContribution = canonicalBindings.Add(binding);
                foreach (var elementRef in elementRefs)
                {
                    if (firstCanonicalContribution)
                    {
                        if (!canonicalByEntity.TryGetValue(elementRef.DgEntityId, out var canonicalStatuses))
                        {
                            canonicalStatuses = new List<EvidenceStatus>();
                            canonicalByEntity.Add(elementRef.DgEntityId, canonicalStatuses);
                            warningsByEntity.Add(elementRef.DgEntityId, new List<string>());
                            detailsByEntity.Add(elementRef.DgEntityId, new List<string>());
                        }
                        // Only genuine outcomes for this original binding contribute to this pair.
                        // Missing typed associations never inherit a boolean or the rule aggregate.
                        if (outcomesByBinding.TryGetValue(binding, out var bindingStatuses))
                        {
                            canonicalStatuses.AddRange(bindingStatuses.Select(o => o.Status));
                            foreach (var outcome in bindingStatuses)
                                if (!string.IsNullOrWhiteSpace(outcome.Detail))
                                    AddUnique(detailsByEntity[elementRef.DgEntityId], outcome.Detail);
                            if (bindingStatuses.Count > 1)
                                AddUnique(warningsByEntity[elementRef.DgEntityId], InconsistentWarning);
                        }
                        else
                        {
                            canonicalStatuses.Add(EvidenceStatus.Unknown);
                            AddUnique(warningsByEntity[elementRef.DgEntityId], UnavailableWarning);
                            AddUnique(detailsByEntity[elementRef.DgEntityId], UnavailableDetail);
                        }
                    }

                    if (!refByEntity.ContainsKey(elementRef.DgEntityId))
                    {
                        refByEntity[elementRef.DgEntityId] = elementRef;
                    }

                    if (!statusByEntity.TryGetValue(elementRef.DgEntityId, out var currentIsFailing))
                    {
                        statusByEntity[elementRef.DgEntityId] = isFailingBinding;
                        bindingByEntity[elementRef.DgEntityId] = binding;
                        continue;
                    }

                    if (isFailingBinding && !currentIsFailing)
                    {
                        bindingByEntity[elementRef.DgEntityId] = binding;
                    }

                    statusByEntity[elementRef.DgEntityId] = currentIsFailing || isFailingBinding;
                }
            }

            var ruleResult = new ValidationPublishRuleResult
            {
                RuleId = rule.Id,
                Passed = result.Passed,
                // Coverage absence cannot trust a default enum; legacy fields are independent.
                Status = unavailable ? EvidenceStatus.Unknown : result.Status,
                Detail = JoinDetails(result.Message, unavailable ? UnavailableDetail : null),
            };
            if (unavailable) ruleResult.Warnings.Add(UnavailableWarning);
            if (inconsistent) ruleResult.Warnings.Add(InconsistentWarning);

            foreach (var pair in statusByEntity.OrderBy(pair => pair.Key, StringComparer.Ordinal))
            {
                var dgEntityId = pair.Key;
                var isFailing = pair.Value;
                if (isFailing)
                {
                    ruleResult.FailedEntityIds.Add(dgEntityId);
                }
                else
                {
                    ruleResult.PassedEntityIds.Add(dgEntityId);
                }

                if (!entityById.TryGetValue(dgEntityId, out var entity))
                {
                    var elementRef = refByEntity[dgEntityId];
                    var bindingForEntity = bindingByEntity.GetValueOrDefault(dgEntityId);
                    var displayName = bindingForEntity is not null
                        ? FailingBindingFormatter.Format(rule, bindingForEntity)
                        : elementRef.DisplayName;
                    entity = new ValidationPublishEntity
                    {
                        DgEntityId = elementRef.DgEntityId,
                        DisplayName = displayName,
                        Geometry = elementRef.Geometry,
                    };
                    entityById[dgEntityId] = entity;
                }
                else
                {
                    var elementRef = refByEntity[dgEntityId];
                    if (entity.DisplayName is null)
                    {
                        var bindingForEntity = bindingByEntity.GetValueOrDefault(dgEntityId);
                        entity.DisplayName = bindingForEntity is not null
                            ? FailingBindingFormatter.Format(rule, bindingForEntity)
                            : elementRef.DisplayName;
                    }

                    if (entity.Geometry is null && elementRef.Geometry is not null)
                    {
                        entity.Geometry = elementRef.Geometry;
                    }
                }

                AddUnique(entity.RuleIds, rule.Id);
                entity.CanonicalStatuses[rule.Id] = StatusRollup.Rollup(canonicalByEntity[dgEntityId]);
                entity.CanonicalWarnings[rule.Id] = warningsByEntity[dgEntityId];
                var canonicalDetail = JoinDetails(detailsByEntity[dgEntityId].ToArray());
                if (canonicalDetail is not null) entity.CanonicalDetails[rule.Id] = canonicalDetail;
                if (isFailing)
                {
                    AddUnique(entity.FailedRuleIds, rule.Id);
                    entity.PassedRuleIds.RemoveAll(value => value.Equals(rule.Id, StringComparison.Ordinal));
                }
                else if (!entity.FailedRuleIds.Contains(rule.Id, StringComparer.Ordinal))
                {
                    AddUnique(entity.PassedRuleIds, rule.Id);
                }
            }

            package.RuleResults.Add(ruleResult);
        }

        // Append only canonical associations after the legacy path so missing-rule order
        // cannot change an existing entity's display name, geometry or legacy lists.
        foreach (var rule in missingRules)
        foreach (var binding in bindings)
        foreach (var elementRef in ExtractElementRefs(binding))
        {
            if (!entityById.TryGetValue(elementRef.DgEntityId, out var entity))
            {
                entity = new ValidationPublishEntity
                {
                    DgEntityId = elementRef.DgEntityId,
                    DisplayName = elementRef.DisplayName,
                    Geometry = elementRef.Geometry,
                };
                entityById.Add(elementRef.DgEntityId, entity);
            }
            AddUnique(entity.RuleIds, rule.Id);
            entity.CanonicalStatuses[rule.Id] = EvidenceStatus.NotEvaluated;
            entity.CanonicalWarnings[rule.Id] = new List<string>();
        }

        foreach (var entity in entityById.Values.OrderBy(entity => entity.DgEntityId, StringComparer.Ordinal))
        {
            package.Entities.Add(entity);
        }

        return package;
    }

    private static string? JoinDetails(params string?[] details)
    {
        var nonempty = details.Where(d => !string.IsNullOrWhiteSpace(d)).Distinct(StringComparer.Ordinal).ToArray();
        return nonempty.Length == 0 ? null : string.Join("\n", nonempty);
    }

    private static List<ElementRef> ExtractElementRefs(BindingRow binding)
    {
        var refs = new Dictionary<string, ElementRef>(StringComparer.Ordinal);
        foreach (var pair in binding.ElementRefsByVar)
        {
            var variableName = pair.Key;
            var elementRef = pair.Value;
            var dgEntityId = ResolveEntityId(binding, variableName, elementRef);
            if (string.IsNullOrWhiteSpace(dgEntityId))
            {
                continue;
            }

            if (!refs.ContainsKey(dgEntityId))
            {
                refs[dgEntityId] = new ElementRef
                {
                    DgEntityId = dgEntityId,
                    Geometry = elementRef.Geometry,
                    DisplayName = string.IsNullOrWhiteSpace(elementRef.DisplayName) ? dgEntityId : elementRef.DisplayName,
                };
            }
        }

        return refs.Values.ToList();
    }

    private static string ResolveEntityId(BindingRow binding, string variableName, ElementRef elementRef)
    {
        if (!string.IsNullOrWhiteSpace(elementRef.DgEntityId))
        {
            return elementRef.DgEntityId;
        }

        if (!binding.ValuesByVar.TryGetValue(variableName, out var value) || value is null)
        {
            return string.Empty;
        }

        return value switch
        {
            string text when !string.IsNullOrWhiteSpace(text) => text.Trim(),
            Guid guid => guid.ToString(),
            sbyte or byte or short or ushort or int or uint or long or ulong or float or double or decimal => Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture) ?? string.Empty,
            _ => string.Empty,
        };
    }

    private static string ResolveProject(IReadOnlyList<Rule> rules)
    {
        var projects = rules
            .Select(rule => string.IsNullOrWhiteSpace(rule.Project) ? "default-project" : rule.Project)
            .Distinct(StringComparer.Ordinal)
            .ToList();

        if (projects.Count > 1)
        {
            throw new InvalidOperationException($"Validation publish requires a single DG project, but received: {string.Join(", ", projects)}");
        }

        return projects[0];
    }

    private static void AddUnique(List<string> items, string value)
    {
        if (!items.Contains(value, StringComparer.Ordinal))
        {
            items.Add(value);
        }
    }
}
