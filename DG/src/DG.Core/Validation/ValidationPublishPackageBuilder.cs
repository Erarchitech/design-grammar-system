using DG.Core.Models;

namespace DG.Core.Validation;

public static class ValidationPublishPackageBuilder
{
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
                package.RuleResults.Add(new ValidationPublishRuleResult
                {
                    RuleId = rule.Id,
                    Passed = false,
                });
                continue;
            }

            var failingBindings = new HashSet<BindingRow>(result.FailingBindings);
            var statusByEntity = new Dictionary<string, bool>(StringComparer.Ordinal);
            var refByEntity = new Dictionary<string, ElementRef>(StringComparer.Ordinal);
            var bindingByEntity = new Dictionary<string, BindingRow>(StringComparer.Ordinal);

            foreach (var binding in bindings)
            {
                var elementRefs = ExtractElementRefs(binding);
                if (elementRefs.Count == 0)
                {
                    continue;
                }

                var isFailingBinding = failingBindings.Contains(binding);
                foreach (var elementRef in elementRefs)
                {
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
            };

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

        foreach (var entity in entityById.Values.OrderBy(entity => entity.DgEntityId, StringComparer.Ordinal))
        {
            package.Entities.Add(entity);
        }

        return package;
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
