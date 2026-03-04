using DG.Core.Models;

namespace DG.Core.Classification;

public static class VariableBinder
{
    public static ClassificationResult BuildBindings(
        IReadOnlyList<Variable> variables,
        IReadOnlyDictionary<string, IReadOnlyList<object?>> valuesByVariable)
    {
        var result = new ClassificationResult();
        if (variables.Count == 0)
        {
            return new ClassificationResult { Status = "No variables provided." };
        }

        foreach (var variable in variables)
        {
            if (string.IsNullOrWhiteSpace(variable.Name) || !valuesByVariable.ContainsKey(variable.Name))
            {
                result.MissingVariables.Add(variable.Name);
            }
        }

        if (result.MissingVariables.Count > 0)
        {
            var missingResult = new ClassificationResult
            {
                Status = $"Missing mappings for: {string.Join(", ", result.MissingVariables)}",
            };
            missingResult.MissingVariables.AddRange(result.MissingVariables);
            return missingResult;
        }

        var rowCount = valuesByVariable.Values.Select(list => list.Count).DefaultIfEmpty(0).Max();
        for (var rowIndex = 0; rowIndex < rowCount; rowIndex++)
        {
            var row = new BindingRow();
            foreach (var variable in variables)
            {
                var values = valuesByVariable[variable.Name];
                object? value = rowIndex < values.Count ? values[rowIndex] : null;
                row.ValuesByVar[variable.Name] = value;
            }

            result.BoundVariables.Add(row);
        }

        var completeResult = new ClassificationResult
        {
            Status = $"Created {result.BoundVariables.Count} binding rows.",
        };
        completeResult.BoundVariables.AddRange(result.BoundVariables);
        return completeResult;
    }
}
