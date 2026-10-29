using DG.Core.Models;
using DG.Core.Services;

namespace DG.Core.Validation;

/// <summary>One checked element of a model: its native identity (Revit UniqueId) and display label.</summary>
public sealed class CheckObject
{
    public string Ref { get; init; } = string.Empty;

    public string? Label { get; init; }
}

/// <summary>One computed property value: the rule and DataProperty it feeds and the element it belongs to.
/// <see cref="Integer"/> wins over <see cref="Number"/> when both are set; neither set means no value.</summary>
public sealed class CheckValue
{
    public string RuleId { get; init; } = string.Empty;

    public string DataPropertyIri { get; init; } = string.Empty;

    public string Ref { get; init; } = string.Empty;

    public long? Integer { get; init; }

    public double? Number { get; init; }
}

/// <summary>The verdict of one rule over a Design State, in the shape VALIDATOR publishes.</summary>
public sealed class CheckRuleOutcome
{
    public Rule Rule { get; init; } = new();

    public RuleEvaluationResult Result { get; init; } = new();

    public ValidationPublishPackage Package { get; init; } = new();

    public List<bool> ValidStatus { get; init; } = new();

    public List<string> ValidStatusNames { get; init; } = new();

    public List<string> FailingLines { get; init; } = new();
}

/// <summary>
/// F-01 (2026-10-29): rule checks of a Revit model without Grasshopper. The DG Revit connector computes the
/// property values in Revit and the dg-evaluator service judges them here. The Design State is composed exactly as
/// OBJECT STATE / PROPERTY STATE / DESIGN STATE compose it (same StateIds, same per-object PropStates), and each rule
/// is evaluated and packaged exactly as VALIDATOR does, so a verdict cannot depend on which path produced it.
/// </summary>
public static class CheckEvaluation
{
    private static readonly RuleEvaluator Evaluator = new();

    public static DesignState BuildDesignState(
        string classIri,
        IReadOnlyList<CheckObject> objects,
        IReadOnlyList<CheckValue> values,
        string? label = null,
        DateTimeOffset? capturedAtUtc = null)
    {
        var captured = capturedAtUtc ?? DateTimeOffset.UtcNow;
        var objStates = new List<ObjState>();
        var known = new HashSet<string>(StringComparer.Ordinal);
        foreach (var obj in objects)
        {
            if (string.IsNullOrWhiteSpace(obj.Ref) || !known.Add(obj.Ref))
                continue;
            objStates.Add(new ObjState
            {
                StateId = DesignStateIdGenerator.ComputeObjectStateIdFromRef(obj.Ref, classIri),
                ObjectRef = obj.Ref,
                Label = obj.Label,
                ClassIri = classIri,
                CapturedAtUtc = captured,
            });
        }

        // PROPERTY STATE numbers its parameters prop_<i> within one component, i.e. per rule and DataProperty.
        var propStates = new List<PropState>();
        var indexByProperty = new Dictionary<(string, string), int>();
        foreach (var value in values)
        {
            if (!known.Contains(value.Ref) || (value.Integer is null && value.Number is null))
                continue;
            var key = (value.RuleId, value.DataPropertyIri);
            indexByProperty.TryGetValue(key, out var i);
            indexByProperty[key] = i + 1;
            var parameter = value.Integer is long integer
                ? new DesignStateParameter
                {
                    ParameterId = $"prop_{i}",
                    DisplayName = value.DataPropertyIri,
                    Type = DesignStateParameterType.Integer,
                    IntegerValue = integer,
                }
                : new DesignStateParameter
                {
                    ParameterId = $"prop_{i}",
                    DisplayName = value.DataPropertyIri,
                    Type = DesignStateParameterType.Number,
                    NumberValue = value.Number,
                };
            propStates.Add(new PropState
            {
                StateId = DesignStateIdGenerator.ComputePropStateId(value.RuleId, value.DataPropertyIri, parameter, value.Ref),
                RuleIri = value.RuleId,
                DataPropertyIri = value.DataPropertyIri,
                ObjectRef = value.Ref,
                PropValue = parameter,
            });
        }

        var members = objStates.Select(o => o.StateId).Concat(propStates.Select(p => p.StateId));
        var state = new DesignState
        {
            StateId = DesignStateIdGenerator.ComputeDesignStateId(members),
            Label = string.IsNullOrWhiteSpace(label) ? null : label!.Trim(),
            CapturedAtUtc = captured,
        };
        state.ObjStates.AddRange(objStates);
        state.PropStates.AddRange(propStates);
        return state;
    }

    public static CheckRuleOutcome EvaluateRule(Rule rule, DesignState designState)
    {
        var bindings = designState.ObjStates.Count > 0
            ? DesignStateBindingService.BuildBindings(rule, designState)
            : new List<BindingRow>();
        var result = Evaluator.EvaluateRule(rule, bindings);
        return new CheckRuleOutcome
        {
            Rule = rule,
            Result = result,
            Package = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { result }, bindings),
            ValidStatus = ValidStatusMapper.PerObjState(designState.ObjStates.Count, result.BindingResults),
            ValidStatusNames = ValidStatusMapper.PerObjStateStatus(designState.ObjStates.Count, result.BindingResults),
            FailingLines = result.FailingBindings.Select(b => FailingBindingFormatter.Format(rule, b)).ToList(),
        };
    }
}
