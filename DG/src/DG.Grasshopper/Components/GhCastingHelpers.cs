#if GRASSHOPPER_SDK
using DG.Core.Models;
using Grasshopper.Kernel.Types;
using System.Collections;
using CoreElementRef = DG.Core.Models.ElementRef;
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

    public static CoreElementRef? TryElementRef(object? input)
    {
        var direct = Unwrap<CoreElementRef>(input);
        if (direct is not null)
        {
            return direct;
        }

        var publicRef = Unwrap<global::DG.ElementRef>(input);
        if (publicRef is not null)
        {
            return new CoreElementRef
            {
                DgEntityId = publicRef.DgEntityId,
                Geometry = publicRef.Geometry,
                DisplayName = publicRef.DisplayName,
            };
        }

        if (input is string text && !string.IsNullOrWhiteSpace(text))
        {
            return new CoreElementRef
            {
                DgEntityId = text.Trim(),
                DisplayName = text.Trim(),
            };
        }

        if (input is Guid guid)
        {
            var id = guid.ToString();
            return new CoreElementRef
            {
                DgEntityId = id,
                DisplayName = id,
            };
        }

        if (TryReadElementRefMembers(input, out var dgEntityId, out var geometry, out var displayName))
        {
            return new CoreElementRef
            {
                DgEntityId = dgEntityId,
                Geometry = geometry,
                DisplayName = displayName,
            };
        }

        return null;
    }

    public static object? ToRawValue(IGH_Goo goo)
    {
        return goo.ScriptVariable();
    }

    public static CoreElementRef? ToElementRef(IGH_Goo goo)
    {
        return TryElementRef(goo.ScriptVariable());
    }

    private static bool TryReadElementRefMembers(
        object? input,
        out string dgEntityId,
        out object? geometry,
        out string? displayName)
    {
        dgEntityId = string.Empty;
        geometry = null;
        displayName = null;

        if (input is null)
        {
            return false;
        }

        if (input is IDictionary dictionary)
        {
            dgEntityId = ReadString(dictionary, "DgEntityId", "dgEntityId", "EntityId", "entityId", "Id", "id");
            if (string.IsNullOrWhiteSpace(dgEntityId))
            {
                return false;
            }

            geometry = ReadValue(dictionary, "Geometry", "geometry");
            displayName = ReadString(dictionary, "DisplayName", "displayName", "Name", "name");
            return true;
        }

        var type = input.GetType();
        dgEntityId = ReadString(type, input, "DgEntityId", "dgEntityId", "EntityId", "entityId", "Id", "id");
        if (string.IsNullOrWhiteSpace(dgEntityId))
        {
            return false;
        }

        geometry = ReadValue(type, input, "Geometry", "geometry");
        displayName = ReadString(type, input, "DisplayName", "displayName", "Name", "name");
        return true;
    }

    private static string ReadString(IDictionary dictionary, params string[] keys)
    {
        foreach (var key in keys)
        {
            if (!dictionary.Contains(key))
            {
                continue;
            }

            var value = dictionary[key];
            if (value is string text && !string.IsNullOrWhiteSpace(text))
            {
                return text.Trim();
            }
        }

        return string.Empty;
    }

    private static object? ReadValue(IDictionary dictionary, params string[] keys)
    {
        foreach (var key in keys)
        {
            if (dictionary.Contains(key))
            {
                return dictionary[key];
            }
        }

        return null;
    }

    private static string ReadString(Type type, object instance, params string[] propertyNames)
    {
        foreach (var propertyName in propertyNames)
        {
            var value = ReadValue(type, instance, propertyName);
            if (value is string text && !string.IsNullOrWhiteSpace(text))
            {
                return text.Trim();
            }
        }

        return string.Empty;
    }

    private static object? ReadValue(Type type, object instance, params string[] propertyNames)
    {
        foreach (var propertyName in propertyNames)
        {
            var property = type.GetProperty(propertyName);
            if (property is null || !property.CanRead)
            {
                continue;
            }

            return property.GetValue(instance);
        }

        return null;
    }
}
#else
namespace DG.Grasshopper.Components;

internal static class GhCastingHelpers
{
}
#endif
