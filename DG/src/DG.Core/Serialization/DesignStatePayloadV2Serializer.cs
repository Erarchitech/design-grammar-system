using System.Globalization;
using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Serialization;

public static class DesignStatePayloadV2Serializer
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    public static string Serialize(DesignState designState)
    {
        ArgumentNullException.ThrowIfNull(designState);

        ValidateDesignState(designState);

        var dto = new DesignStatePayloadV2Dto
        {
            Version = "2",
            StateId = designState.StateId,
            CapturedAtUtc = designState.CapturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture),
            ObjStates = designState.ObjStates
                .OrderBy(o => o.StateId, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
            ParamStates = designState.ParamStates
                .OrderBy(p => p.StateId, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
            PropStates = designState.PropStates
                .OrderBy(p => p.StateId, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
        };

        return JsonSerializer.Serialize(dto, Options);
    }

    public static DesignState Deserialize(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            throw new InvalidOperationException("Design state v2 payload must not be empty.");
        }

        DesignStatePayloadV2Dto? dto;
        try
        {
            dto = JsonSerializer.Deserialize<DesignStatePayloadV2Dto>(json, Options);
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException("Design state v2 payload is not valid JSON.", ex);
        }

        if (dto is null)
        {
            throw new InvalidOperationException("Design state v2 payload is empty.");
        }

        if (dto.Version != "2")
        {
            throw new InvalidOperationException($"Unsupported state payload version. Expected '2', got '{dto.Version ?? "null"}'.");
        }

        if (!DateTimeOffset.TryParse(dto.CapturedAtUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var capturedAt))
        {
            throw new InvalidOperationException("CapturedAtUtc is required and must be a valid ISO 8601 round-trip timestamp.");
        }

        var designState = new DesignState
        {
            StateId = dto.StateId ?? string.Empty,
            CapturedAtUtc = capturedAt.ToUniversalTime(),
        };

        foreach (var objDto in dto.ObjStates ?? Enumerable.Empty<ObjStateDto>())
        {
            designState.ObjStates.Add(FromDto(objDto));
        }

        foreach (var paramDto in dto.ParamStates ?? Enumerable.Empty<ParamStateDto>())
        {
            designState.ParamStates.Add(FromDto(paramDto));
        }

        foreach (var propDto in dto.PropStates ?? Enumerable.Empty<PropStateDto>())
        {
            designState.PropStates.Add(FromDto(propDto));
        }

        ValidateDeserialized(designState);
        return designState;
    }

    private static void ValidateDesignState(DesignState designState)
    {
        if (designState.CapturedAtUtc == default)
        {
            throw new InvalidOperationException("CapturedAtUtc is required.");
        }

        if (string.IsNullOrWhiteSpace(designState.StateId))
        {
            throw new InvalidOperationException("StateId is required.");
        }

        foreach (var objState in designState.ObjStates)
        {
            if (string.IsNullOrWhiteSpace(objState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every ObjState.");
            }

            if (string.IsNullOrWhiteSpace(objState.ObjectRef))
            {
                throw new InvalidOperationException($"ObjectRef is required for ObjState '{objState.StateId}'.");
            }

            if (objState.CapturedAtUtc == default)
            {
                throw new InvalidOperationException($"CapturedAtUtc is required for ObjState '{objState.StateId}'.");
            }
        }

        foreach (var paramState in designState.ParamStates)
        {
            if (string.IsNullOrWhiteSpace(paramState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every ParamState.");
            }

            if (paramState.CapturedAtUtc == default)
            {
                throw new InvalidOperationException($"CapturedAtUtc is required for ParamState '{paramState.StateId}'.");
            }

            foreach (var parameter in paramState.Parameters)
            {
                ValidateParameter(parameter);
            }
        }

        foreach (var propState in designState.PropStates)
        {
            if (string.IsNullOrWhiteSpace(propState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every PropState.");
            }

            if (string.IsNullOrWhiteSpace(propState.RuleIri))
            {
                throw new InvalidOperationException($"RuleIri is required for PropState '{propState.StateId}'.");
            }

            if (string.IsNullOrWhiteSpace(propState.DataPropertyIri))
            {
                throw new InvalidOperationException($"DataPropertyIri is required for PropState '{propState.StateId}'.");
            }

            if (propState.PropValue is not null)
            {
                ValidateParameter(propState.PropValue);
            }
        }
    }

    private static void ValidateDeserialized(DesignState designState)
    {
        if (string.IsNullOrWhiteSpace(designState.StateId))
        {
            throw new InvalidOperationException("StateId is required in deserialized DesignState.");
        }

        if (designState.CapturedAtUtc == default)
        {
            throw new InvalidOperationException("CapturedAtUtc is required in deserialized DesignState.");
        }

        foreach (var objState in designState.ObjStates)
        {
            if (string.IsNullOrWhiteSpace(objState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every deserialized ObjState.");
            }
        }

        foreach (var paramState in designState.ParamStates)
        {
            if (string.IsNullOrWhiteSpace(paramState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every deserialized ParamState.");
            }
        }

        foreach (var propState in designState.PropStates)
        {
            if (string.IsNullOrWhiteSpace(propState.StateId))
            {
                throw new InvalidOperationException("StateId is required for every deserialized PropState.");
            }
        }
    }

    private static void ValidateParameter(DesignStateParameter parameter)
    {
        if (string.IsNullOrWhiteSpace(parameter.ParameterId))
        {
            throw new InvalidOperationException("ParameterId is required for every design state parameter.");
        }

        if (string.IsNullOrWhiteSpace(parameter.DisplayName))
        {
            throw new InvalidOperationException($"DisplayName is required for parameter '{parameter.ParameterId}'.");
        }

        switch (parameter.Type)
        {
            case DesignStateParameterType.Number:
                if (!parameter.NumberValue.HasValue || parameter.IntegerValue.HasValue || parameter.BooleanValue.HasValue)
                {
                    throw new InvalidOperationException($"Parameter '{parameter.ParameterId}' with type number must provide only NumberValue.");
                }

                break;
            case DesignStateParameterType.Integer:
                if (!parameter.IntegerValue.HasValue || parameter.NumberValue.HasValue || parameter.BooleanValue.HasValue)
                {
                    throw new InvalidOperationException($"Parameter '{parameter.ParameterId}' with type integer must provide only IntegerValue.");
                }

                break;
            case DesignStateParameterType.Boolean:
                if (!parameter.BooleanValue.HasValue || parameter.NumberValue.HasValue || parameter.IntegerValue.HasValue)
                {
                    throw new InvalidOperationException($"Parameter '{parameter.ParameterId}' with type boolean must provide only BooleanValue.");
                }

                break;
            default:
                throw new InvalidOperationException($"Unsupported parameter type '{parameter.Type}'.");
        }
    }

    private static ObjStateDto ToDto(ObjState objState)
    {
        return new ObjStateDto
        {
            StateId = objState.StateId,
            ObjectRef = objState.ObjectRef,
            Label = objState.Label,
            CapturedAtUtc = objState.CapturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture),
        };
    }

    private static ParamStateDto ToDto(ParamState paramState)
    {
        return new ParamStateDto
        {
            StateId = paramState.StateId,
            CapturedAtUtc = paramState.CapturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture),
            Parameters = paramState.Parameters
                .OrderBy(p => p.ParameterId, StringComparer.Ordinal)
                .Select(ParamToDto)
                .ToList(),
        };
    }

    private static PropStateDto ToDto(PropState propState)
    {
        return new PropStateDto
        {
            StateId = propState.StateId,
            RuleIri = propState.RuleIri,
            DataPropertyIri = propState.DataPropertyIri,
            PropValue = propState.PropValue is not null ? ParamToDto(propState.PropValue) : null,
        };
    }

    private static ParameterDto ParamToDto(DesignStateParameter parameter)
    {
        return parameter.Type switch
        {
            DesignStateParameterType.Number => new ParameterDto
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Type = "number",
                Value = parameter.NumberValue,
            },
            DesignStateParameterType.Integer => new ParameterDto
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Type = "integer",
                Value = parameter.IntegerValue,
            },
            DesignStateParameterType.Boolean => new ParameterDto
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Type = "boolean",
                Value = parameter.BooleanValue,
            },
            _ => throw new InvalidOperationException($"Unsupported design state parameter type: {parameter.Type}"),
        };
    }

    private static ObjState FromDto(ObjStateDto dto)
    {
        if (!DateTimeOffset.TryParse(dto.CapturedAtUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var capturedAt))
        {
            throw new InvalidOperationException($"CapturedAtUtc is required for ObjState '{dto.StateId}' and must be a valid ISO 8601 round-trip timestamp.");
        }

        return new ObjState
        {
            StateId = dto.StateId ?? string.Empty,
            ObjectRef = dto.ObjectRef ?? string.Empty,
            Label = dto.Label,
            CapturedAtUtc = capturedAt.ToUniversalTime(),
        };
    }

    private static ParamState FromDto(ParamStateDto dto)
    {
        if (!DateTimeOffset.TryParse(dto.CapturedAtUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var capturedAt))
        {
            throw new InvalidOperationException($"CapturedAtUtc is required for ParamState '{dto.StateId}' and must be a valid ISO 8601 round-trip timestamp.");
        }

        var paramState = new ParamState
        {
            StateId = dto.StateId ?? string.Empty,
            CapturedAtUtc = capturedAt.ToUniversalTime(),
        };

        foreach (var parameterDto in dto.Parameters ?? Enumerable.Empty<ParameterDto>())
        {
            paramState.Parameters.Add(ParamFromDto(parameterDto));
        }

        return paramState;
    }

    private static PropState FromDto(PropStateDto dto)
    {
        return new PropState
        {
            StateId = dto.StateId ?? string.Empty,
            RuleIri = dto.RuleIri ?? string.Empty,
            DataPropertyIri = dto.DataPropertyIri ?? string.Empty,
            PropValue = dto.PropValue is not null ? ParamFromDto(dto.PropValue) : null,
        };
    }

    private static DesignStateParameter ParamFromDto(ParameterDto dto)
    {
        if (dto is null)
        {
            throw new InvalidOperationException("Parameter entry is required.");
        }

        var typeToken = (dto.Type ?? string.Empty).Trim().ToLowerInvariant();
        return typeToken switch
        {
            "number" => new DesignStateParameter
            {
                ParameterId = dto.ParameterId ?? string.Empty,
                DisplayName = dto.DisplayName ?? string.Empty,
                Type = DesignStateParameterType.Number,
                NumberValue = ParseNumber(dto.Value),
            },
            "integer" => new DesignStateParameter
            {
                ParameterId = dto.ParameterId ?? string.Empty,
                DisplayName = dto.DisplayName ?? string.Empty,
                Type = DesignStateParameterType.Integer,
                IntegerValue = ParseInteger(dto.Value),
            },
            "boolean" => new DesignStateParameter
            {
                ParameterId = dto.ParameterId ?? string.Empty,
                DisplayName = dto.DisplayName ?? string.Empty,
                Type = DesignStateParameterType.Boolean,
                BooleanValue = ParseBoolean(dto.Value),
            },
            _ => throw new InvalidOperationException($"Unsupported parameter type '{dto.Type}'. Allowed types are number, integer, boolean."),
        };
    }

    private static JsonElement RequireJsonElement(object? value)
    {
        if (value is not JsonElement element)
        {
            throw new InvalidOperationException("Parameter value is required.");
        }

        return element;
    }

    private static double ParseNumber(object? value)
    {
        var element = RequireJsonElement(value);
        if (element.ValueKind is not JsonValueKind.Number)
        {
            throw new InvalidOperationException("number parameter value must be numeric.");
        }

        if (!element.TryGetDouble(out var parsed))
        {
            throw new InvalidOperationException("number parameter value is not a valid floating-point number.");
        }

        return parsed;
    }

    private static long ParseInteger(object? value)
    {
        var element = RequireJsonElement(value);
        if (element.ValueKind is not JsonValueKind.Number)
        {
            throw new InvalidOperationException("integer parameter value must be numeric.");
        }

        if (!element.TryGetInt64(out var parsed))
        {
            throw new InvalidOperationException("integer parameter value must be a whole number.");
        }

        return parsed;
    }

    private static bool ParseBoolean(object? value)
    {
        var element = RequireJsonElement(value);
        if (element.ValueKind is not JsonValueKind.True && element.ValueKind is not JsonValueKind.False)
        {
            throw new InvalidOperationException("boolean parameter value must be true or false.");
        }

        return element.GetBoolean();
    }

    private sealed class DesignStatePayloadV2Dto
    {
        public string? Version { get; init; }

        public string? StateId { get; init; }

        public string? CapturedAtUtc { get; init; }

        public List<ObjStateDto>? ObjStates { get; init; }

        public List<ParamStateDto>? ParamStates { get; init; }

        public List<PropStateDto>? PropStates { get; init; }
    }

    private sealed class ObjStateDto
    {
        public string? StateId { get; init; }

        public string? ObjectRef { get; init; }

        public string? Label { get; init; }

        public string? CapturedAtUtc { get; init; }
    }

    private sealed class ParamStateDto
    {
        public string? StateId { get; init; }

        public string? CapturedAtUtc { get; init; }

        public List<ParameterDto>? Parameters { get; init; }
    }

    private sealed class PropStateDto
    {
        public string? StateId { get; init; }

        public string? RuleIri { get; init; }

        public string? DataPropertyIri { get; init; }

        public ParameterDto? PropValue { get; init; }
    }

    private sealed class ParameterDto
    {
        public string? ParameterId { get; init; }

        public string? DisplayName { get; init; }

        public string? Type { get; init; }

        public object? Value { get; init; }
    }
}
