using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Services;

public static class DesignStateBindingService
{
    public static List<BindingRow> BuildBindings(Rule rule, DesignState designState)
    {
        var objectVars = new List<string>();
        var propertyVars = new List<string>();

        // Step 1: Classify each variable using VariableTypeInferrer.Infer()
        foreach (var variable in rule.Variables)
        {
            if (string.IsNullOrWhiteSpace(variable.Name))
                continue;

            var kind = VariableTypeInferrer.Infer(rule, variable.Name);

            if (kind == VariableKind.Object)
            {
                objectVars.Add(variable.Name);
            }
            else if (kind == VariableKind.Property)
            {
                propertyVars.Add(variable.Name);
            }
            else
            {
                // null — check Builtin-only (D-07) or throw (D-06)
                if (!IsBuiltinOnlyVariable(rule, variable.Name))
                {
                    throw new InvalidOperationException(
                        ErrorMessageTemplates.RuleVariableUnclassified(rule.Id, variable.Name));
                }
                // Builtin-only variables are excluded from bindings per D-07
            }
        }

        var results = new List<BindingRow>();

        // Step 2: Build BindingRows from ObjStates with Class IRI matching (D-05)
        if (objectVars.Count > 0)
        {
            // Resolve each Object variable's target Class IRI from the Rule
            var objectVarClassIris = new Dictionary<string, string?>(StringComparer.Ordinal);
            foreach (var objVar in objectVars)
            {
                objectVarClassIris[objVar] = GetObjectVarClassIri(rule, objVar);
            }

            if (designState.ObjStates.Count == 0)
            {
                throw new InvalidOperationException(
                    ErrorMessageTemplates.BindingServiceNoObjectBindings(rule.Id));
            }

            foreach (var objState in designState.ObjStates)
            {
                var matched = false;
                var row = new BindingRow();

                foreach (var objVar in objectVars)
                {
                    var targetClassIri = objectVarClassIris[objVar];
                    // Match when:
                    //   - No class constraint (targetClassIri is null): match ALL ObjStates
                    //   - Class constraint present: match only ObjStates with matching ClassIri
                    if (targetClassIri is null ||
                        (objState.ClassIri is not null &&
                         string.Equals(objState.ClassIri, targetClassIri, StringComparison.Ordinal)))
                    {
                        matched = true;
                        row.ValuesByVar[objVar] = objState.ObjectRef;
                        row.ElementRefsByVar[objVar] = new ElementRef
                        {
                            DgEntityId = objState.ObjectRef,
                            DisplayName = objState.Label ?? objState.ObjectRef,
                        };
                    }
                }

                if (matched)
                {
                    results.Add(row);
                }
            }
        }

        // Step 3: Apply Property values from PropStates onto existing rows
        ApplyPropertyValues(results, rule, propertyVars, designState.PropStates);

        // Step 4: Property-only rule with no ObjStates — create a single row
        if (objectVars.Count == 0 && propertyVars.Count > 0 && results.Count == 0)
        {
            var row = new BindingRow();
            ApplyPropertyValuesForRow(row, rule, propertyVars, designState.PropStates);
            if (row.ValuesByVar.Count > 0)
            {
                results.Add(row);
            }
        }

        return results;
    }

    private static void ApplyPropertyValues(
        List<BindingRow> rows,
        Rule rule,
        List<string> propertyVars,
        List<PropState> propStates)
    {
        if (rows.Count == 0 || propertyVars.Count == 0)
            return;

        foreach (var propState in propStates)
        {
            if (!string.Equals(propState.RuleIri, rule.Id, StringComparison.Ordinal))
                continue;

            foreach (var propVar in propertyVars)
            {
                var dataPropertyIri = GetDataPropertyIri(rule, propVar);
                if (dataPropertyIri is null)
                    continue;

                if (!string.Equals(propState.DataPropertyIri, dataPropertyIri, StringComparison.Ordinal))
                    continue;

                var value = ExtractPropValue(propState);

                foreach (var row in rows)
                {
                    row.ValuesByVar[propVar] = value;
                }
            }
        }
    }

    private static void ApplyPropertyValuesForRow(
        BindingRow row,
        Rule rule,
        List<string> propertyVars,
        List<PropState> propStates)
    {
        foreach (var propState in propStates)
        {
            if (!string.Equals(propState.RuleIri, rule.Id, StringComparison.Ordinal))
                continue;

            foreach (var propVar in propertyVars)
            {
                var dataPropertyIri = GetDataPropertyIri(rule, propVar);
                if (dataPropertyIri is null)
                    continue;

                if (!string.Equals(propState.DataPropertyIri, dataPropertyIri, StringComparison.Ordinal))
                    continue;

                row.ValuesByVar[propVar] = ExtractPropValue(propState);
            }
        }
    }

    private static object? ExtractPropValue(PropState propState)
    {
        if (propState.PropValue is null)
            return null;

        if (propState.PropValue.NumberValue.HasValue)
            return propState.PropValue.NumberValue.Value;

        if (propState.PropValue.IntegerValue.HasValue)
            return propState.PropValue.IntegerValue.Value;

        if (propState.PropValue.BooleanValue.HasValue)
            return propState.PropValue.BooleanValue.Value;

        return null;
    }

    private static string? GetObjectVarClassIri(Rule rule, string variableName)
    {
        foreach (var atom in rule.BodyAtoms)
        {
            if (atom.Type != "ClassAtom")
                continue;

            foreach (var arg in atom.Args)
            {
                if (arg.Kind == ArgKind.Variable && arg.Pos == 1 &&
                    string.Equals(arg.Value, variableName, StringComparison.Ordinal))
                {
                    return atom.PredicateIri ?? atom.PredicateLabel ?? atom.Id;
                }
            }
        }

        return null;
    }

    private static string? GetDataPropertyIri(Rule rule, string variableName)
    {
        foreach (var atom in rule.BodyAtoms)
        {
            if (atom.Type != "DataPropertyAtom")
                continue;

            foreach (var arg in atom.Args)
            {
                if (arg.Kind == ArgKind.Variable && arg.Pos == 2 &&
                    string.Equals(arg.Value, variableName, StringComparison.Ordinal))
                {
                    return atom.PredicateIri ?? atom.PredicateLabel ?? atom.Id;
                }
            }
        }

        return null;
    }

    private static bool IsBuiltinOnlyVariable(Rule rule, string variableName)
    {
        var allAtoms = rule.BodyAtoms.Concat(rule.HeadAtoms);
        var foundInBuiltin = false;
        var foundInNonBuiltin = false;

        foreach (var atom in allAtoms)
        {
            var isBuiltin = atom.Type == "BuiltinAtom";

            foreach (var arg in atom.Args)
            {
                if (arg.Kind == ArgKind.Variable &&
                    string.Equals(arg.Value, variableName, StringComparison.Ordinal))
                {
                    if (isBuiltin)
                        foundInBuiltin = true;
                    else
                        foundInNonBuiltin = true;
                }
            }
        }

        return foundInBuiltin && !foundInNonBuiltin;
    }
}
