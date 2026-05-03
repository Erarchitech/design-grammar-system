using System.Globalization;
using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Serialization;

public static class DesignStateJsonSerializer
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    public static string Serialize(DesignStateSnapshot snapshot)
    {
        ArgumentNullException.ThrowIfNull(snapshot);

        ValidateSnapshot(snapshot);

        var dto = new SnapshotDto
        {
            StateId = snapshot.StateId,
            CapturedAtUtc = snapshot.CapturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture),
            Parameters = snapshot.Parameters
                .OrderBy(parameter => parameter.ParameterId, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
        };

        return JsonSerializer.Serialize(dto, Options);
    }

    public static DesignStateSnapshot Deserialize(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            throw new InvalidOperationException("Design state payload must not be empty.");
        }

        SnapshotDto? dto;
        try
        {
            dto = JsonSerializer.Deserialize<SnapshotDto>(json, Options);
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException("Design state payload is not valid JSON.", ex);
        }

        if (dto is null)
        {
            throw new InvalidOperationException("Design state payload is empty.");
        }

        if (!DateTimeOffset.TryParse(dto.CapturedAtUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var capturedAt))
        {
            throw new InvalidOperationException("CapturedAtUtc is required and must be a valid ISO 8601 round-trip timestamp.");
        }

        var snapshot = new DesignStateSnapshot
        {
            StateId = dto.StateId ?? string.Empty,
            CapturedAtUtc = capturedAt.ToUniversalTime(),
        };

        foreach (var parameterDto in dto.Parameters ?? Enumerable.Empty<ParameterDto>())
        {
            snapshot.Parameters.Add(FromDto(parameterDto));
        }

        ValidateSnapshot(snapshot);
        return snapshot;
    }

    private static ParameterDto ToDto(DesignStateParameter parameter)
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

    private static DesignStateParameter FromDto(ParameterDto dto)
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

    private static void ValidateSnapshot(DesignStateSnapshot snapshot)
    {
        if (snapshot.CapturedAtUtc == default)
        {
            throw new InvalidOperationException("CapturedAtUtc is required.");
        }

        foreach (var parameter in snapshot.Parameters)
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

    private sealed class SnapshotDto
    {
        public string? StateId { get; init; }

        public string? CapturedAtUtc { get; init; }

        public List<ParameterDto>? Parameters { get; init; }
    }

    private sealed class ParameterDto
    {
        public string? ParameterId { get; init; }

        public string? DisplayName { get; init; }

        public string? Type { get; init; }

        public object? Value { get; init; }
    }
}
