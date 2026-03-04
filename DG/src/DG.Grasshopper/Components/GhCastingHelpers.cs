#if GRASSHOPPER_SDK
using DG.Core.Models;
using Grasshopper.Kernel.Types;
using CoreRule = DG.Core.Models.Rule;
using CoreVariable = DG.Core.Models.Variable;

namespace DG.Grasshopper.Components;

internal static class GhCastingHelpers
{
    public static T? Unwrap<T>(object? input)
        where T : class
    {
        return input switch
        {
            null => null,
            T typed => typed,
            GH_ObjectWrapper wrapper => wrapper.Value as T,
            _ => null,
        };
    }

    public static CoreRule? TryRule(object? input)
    {
        var direct = Unwrap<CoreRule>(input);
        if (direct is not null)
        {
            return direct;
        }

        var publicRule = Unwrap<global::DG.Rule>(input);
        if (publicRule is null)
        {
            return null;
        }

        return new CoreRule
        {
            Id = publicRule.Id,
            Name = publicRule.Name,
            Description = publicRule.Description,
            Kind = publicRule.Kind,
            Text = publicRule.Text,
            Swrl = publicRule.Swrl,
            Project = publicRule.Project,
            Graph = publicRule.Graph,
        };
    }

    public static CoreVariable? TryVariable(object? input)
    {
        var direct = Unwrap<CoreVariable>(input);
        if (direct is not null)
        {
            return direct;
        }

        var publicVar = Unwrap<global::DG.Variable>(input);
        return publicVar is null
            ? null
            : new CoreVariable
            {
                Name = publicVar.Name,
                InferredDatatype = publicVar.InferredDatatype,
            };
    }

    public static BindingRow? TryBindingRow(object? input)
    {
        return Unwrap<BindingRow>(input);
    }

    public static object? ToRawValue(IGH_Goo goo)
    {
        return goo.ScriptVariable();
    }
}
#else
namespace DG.Grasshopper.Components;

internal static class GhCastingHelpers
{
}
#endif
