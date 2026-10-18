using System.Globalization;

namespace DG.Core.Mapping;

/// <summary>
/// Pairs a calculation output with an element stream (Phase 1303, D-37). Both are keyed
/// "path|index" (one value per branch → index 0; a single list → item index). Paths match when
/// both key sets are equal; agreement is, per element property the plugin computed from the
/// stream's own geometry (hasAspectRatio, hasVertexCount …), the share of elements whose value
/// equals the output value. Pure; no Grasshopper dependency.
/// </summary>
public static class MappingMeasureMatcher
{
    public static string Key(string path, int index) => path + "|" + index.ToString(CultureInfo.InvariantCulture);

    public static bool Equal(double a, double b) => Math.Abs(a - b) <= 1e-6 + 1e-3 * Math.Max(Math.Abs(a), Math.Abs(b));

    public static MappingMeasureStream Match(
        string stream,
        IReadOnlyDictionary<string, double> measure,
        IReadOnlyDictionary<string, IReadOnlyDictionary<string, object>> elementProperties)
    {
        var pathMatch = measure.Count > 0
            && measure.Count == elementProperties.Count
            && measure.Keys.All(elementProperties.ContainsKey);
        var values = measure.Values.ToList();
        var constant = values.Count > 1 && values.All(v => Equal(v, values[0]));
        var agreement = new Dictionary<string, double>(StringComparer.Ordinal);
        if (pathMatch)
        {
            var propertyNames = elementProperties.Values.SelectMany(p => p.Keys).Distinct(StringComparer.Ordinal);
            foreach (var name in propertyNames)
            {
                var equal = 0;
                foreach (var (key, value) in measure)
                {
                    if (elementProperties[key].TryGetValue(name, out var raw) && ToDouble(raw) is { } v && Equal(v, value))
                    {
                        equal++;
                    }
                }

                var share = (double)equal / measure.Count;
                if (share > 0)
                {
                    agreement[name] = share;
                }
            }
        }

        return new MappingMeasureStream { Stream = stream, PathMatch = pathMatch, Constant = constant, Agreement = agreement };
    }

    private static double? ToDouble(object? raw) => raw switch
    {
        double d => d,
        float f => f,
        int i => i,
        long l => l,
        bool => null,
        _ => double.TryParse(Convert.ToString(raw, CultureInfo.InvariantCulture), NumberStyles.Float, CultureInfo.InvariantCulture, out var v) ? v : null,
    };
}
