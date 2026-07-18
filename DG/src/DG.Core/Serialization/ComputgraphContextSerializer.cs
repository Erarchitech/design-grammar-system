using System.Text.Json;
using DG.Core.Models.Computgraph;

namespace DG.Core.Serialization;

public static class ComputgraphContextSerializer
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    public static string Serialize(CgContext context)
    {
        ArgumentNullException.ThrowIfNull(context);

        ValidateContext(context);

        var dto = ToDto(context);

        return JsonSerializer.Serialize(dto, Options);
    }

    public static CgContext Deserialize(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            throw new InvalidOperationException("cgContext payload must not be empty.");
        }

        CgContextDto? dto;
        try
        {
            dto = JsonSerializer.Deserialize<CgContextDto>(json, Options);
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException("cgContext payload is not valid JSON.", ex);
        }

        if (dto is null)
        {
            throw new InvalidOperationException("cgContext payload is empty.");
        }

        if (dto.SchemaVersion != "cg-context-1")
        {
            throw new InvalidOperationException(
                $"Unsupported cgContext schema version. Expected 'cg-context-1', got '{dto.SchemaVersion ?? "null"}'.");
        }

        var context = FromDto(dto);
        ValidateDeserialized(context);
        return context;
    }

    private static void ValidateContext(CgContext context)
    {
        if (context.SchemaVersion != "cg-context-1")
        {
            throw new InvalidOperationException(
                $"Unsupported cgContext schema version. Expected 'cg-context-1', got '{context.SchemaVersion ?? "null"}'.");
        }

        if (string.IsNullOrWhiteSpace(context.Definition.DocumentId))
        {
            throw new InvalidOperationException("Definition.DocumentId is required.");
        }

        if (string.IsNullOrWhiteSpace(context.Definition.FileName))
        {
            throw new InvalidOperationException("Definition.FileName is required.");
        }
    }

    private static CgContextDto ToDto(CgContext context)
    {
        return new CgContextDto
        {
            SchemaVersion = context.SchemaVersion,
            Project = context.Project,
            Definition = ToDto(context.Definition),
            Object = context.Object is not null ? ToDto(context.Object) : null,
            Algorithms = context.Algorithms
                .OrderBy(a => a.Index)
                .Select(ToDto)
                .ToList(),
            Untagged = ToDto(context.Untagged),
            Nodes = context.Nodes
                .OrderBy(n => n.InstanceId, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
            Wires = context.Wires
                .OrderBy(w => w.FromNode, StringComparer.Ordinal)
                .ThenBy(w => w.FromParam, StringComparer.Ordinal)
                .ThenBy(w => w.ToNode, StringComparer.Ordinal)
                .ThenBy(w => w.ToParam, StringComparer.Ordinal)
                .Select(ToDto)
                .ToList(),
            Warnings = context.Warnings
                .OrderBy(w => w, StringComparer.Ordinal)
                .ToList(),
        };
    }

    private static CgDefinitionDto ToDto(CgDefinition definition)
    {
        return new CgDefinitionDto
        {
            DocumentId = definition.DocumentId,
            FileName = definition.FileName,
            CapturedAt = definition.CapturedAt,
        };
    }

    private static CgObjectDto ToDto(CgObject obj)
    {
        return new CgObjectDto
        {
            Name = obj.Name,
            ClassIri = obj.ClassIri,
            Source = obj.Source,
            DgId = obj.DgId,
        };
    }

    private static CgAlgorithmDto ToDto(CgAlgorithm algorithm)
    {
        return new CgAlgorithmDto
        {
            Index = algorithm.Index,
            Name = algorithm.Name,
            Procedures = algorithm.Procedures
                .OrderBy(p => p.Index)
                .Select(ToDto)
                .ToList(),
        };
    }

    private static CgProcedureDto ToDto(CgProcedure procedure)
    {
        return new CgProcedureDto
        {
            Id = procedure.Id,
            Index = procedure.Index,
            Name = procedure.Name,
            Source = procedure.Source,
            DgId = procedure.DgId,
            MemberIds = procedure.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
            Patterns = procedure.Patterns.OrderBy(p => p.Id, StringComparer.Ordinal).Select(ToDto).ToList(),
            Parameters = procedure.Parameters.OrderBy(p => p.Id, StringComparer.Ordinal).Select(ToDto).ToList(),
            Interfaces = procedure.Interfaces.OrderBy(i => i.Id, StringComparer.Ordinal).Select(ToDto).ToList(),
        };
    }

    private static CgPatternDto ToDto(CgPattern pattern)
    {
        return new CgPatternDto
        {
            Id = pattern.Id,
            Label = pattern.Label,
            Name = pattern.Name,
            HostPatternId = pattern.HostPatternId,
            MemberIds = pattern.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
            Source = pattern.Source,
            DgId = pattern.DgId,
        };
    }

    private static CgParameterDto ToDto(CgParameter parameter)
    {
        return new CgParameterDto
        {
            Id = parameter.Id,
            Kind = ParamKindToDto(parameter.Kind),
            Name = parameter.Name,
            DataType = parameter.DataType.HasValue ? ParamDataTypeToDto(parameter.DataType.Value) : null,
            Domain = parameter.Domain is not null ? ToDto(parameter.Domain) : null,
            MemberIds = parameter.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
            Source = parameter.Source,
            DgId = parameter.DgId,
        };
    }

    private static SliderDomainDto ToDto(SliderDomain domain)
    {
        return new SliderDomainDto
        {
            Min = domain.Min,
            Max = domain.Max,
            Step = domain.Step,
        };
    }

    private static CgInterfaceDto ToDto(CgInterface iface)
    {
        return new CgInterfaceDto
        {
            Id = iface.Id,
            Name = iface.Name,
            IfaceType = IfaceTypeToDto(iface.IfaceType),
            MemberIds = iface.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
            Source = iface.Source,
            DgId = iface.DgId,
        };
    }

    private static CgNodeDto ToDto(CgNode node)
    {
        return new CgNodeDto
        {
            InstanceId = node.InstanceId,
            ComponentGuid = node.ComponentGuid,
            Name = node.Name,
            Nickname = node.Nickname,
            Position = node.Position,
            Slider = node.Slider is not null ? ToDto(node.Slider) : null,
            IsIntegerSlider = node.IsIntegerSlider,
        };
    }

    private static CgWireDto ToDto(CgWire wire)
    {
        return new CgWireDto
        {
            FromNode = wire.FromNode,
            FromParam = wire.FromParam,
            ToNode = wire.ToNode,
            ToParam = wire.ToParam,
        };
    }

    private static CgUntaggedDto ToDto(CgUntagged untagged)
    {
        return new CgUntaggedDto
        {
            NodeIds = untagged.NodeIds.OrderBy(n => n, StringComparer.Ordinal).ToList(),
            Groups = untagged.Groups.OrderBy(g => g.Nickname, StringComparer.Ordinal).Select(ToDto).ToList(),
        };
    }

    private static CgUntaggedGroupDto ToDto(CgUntaggedGroup group)
    {
        return new CgUntaggedGroupDto
        {
            Nickname = group.Nickname,
            MemberIds = group.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
        };
    }

    private static string ParamKindToDto(ParamKind kind) => kind switch
    {
        ParamKind.Variable => "Variable",
        ParamKind.Constant => "Constant",
        ParamKind.Emergent => "Emergent",
        _ => throw new InvalidOperationException($"Unsupported ParamKind: {kind}"),
    };

    private static string ParamDataTypeToDto(ParamDataType dataType) => dataType switch
    {
        ParamDataType.Float => "Float",
        ParamDataType.Integer => "Integer",
        ParamDataType.Text => "Text",
        ParamDataType.Boolean => "Boolean",
        ParamDataType.Geometry => "Geometry",
        _ => throw new InvalidOperationException($"Unsupported ParamDataType: {dataType}"),
    };

    private static string IfaceTypeToDto(IfaceType ifaceType) => ifaceType switch
    {
        IfaceType.Input => "Input",
        IfaceType.Output => "Output",
        _ => throw new InvalidOperationException($"Unsupported IfaceType: {ifaceType}"),
    };

    private static void ValidateDeserialized(CgContext context)
    {
        if (string.IsNullOrWhiteSpace(context.Definition.DocumentId))
        {
            throw new InvalidOperationException("Definition.DocumentId is required in deserialized cgContext.");
        }

        if (string.IsNullOrWhiteSpace(context.Definition.FileName))
        {
            throw new InvalidOperationException("Definition.FileName is required in deserialized cgContext.");
        }
    }

    private static CgContext FromDto(CgContextDto dto)
    {
        var context = new CgContext
        {
            SchemaVersion = dto.SchemaVersion ?? string.Empty,
            Project = dto.Project ?? string.Empty,
            Definition = FromDto(dto.Definition ?? new CgDefinitionDto()),
            Object = dto.Object is not null ? FromDto(dto.Object) : null,
            Untagged = FromDto(dto.Untagged ?? new CgUntaggedDto()),
        };

        foreach (var algorithmDto in dto.Algorithms ?? Enumerable.Empty<CgAlgorithmDto>())
        {
            context.Algorithms.Add(FromDto(algorithmDto));
        }

        foreach (var nodeDto in dto.Nodes ?? Enumerable.Empty<CgNodeDto>())
        {
            context.Nodes.Add(FromDto(nodeDto));
        }

        foreach (var wireDto in dto.Wires ?? Enumerable.Empty<CgWireDto>())
        {
            context.Wires.Add(FromDto(wireDto));
        }

        foreach (var warning in dto.Warnings ?? Enumerable.Empty<string>())
        {
            context.Warnings.Add(warning);
        }

        return context;
    }

    private static CgDefinition FromDto(CgDefinitionDto dto)
    {
        return new CgDefinition
        {
            DocumentId = dto.DocumentId ?? string.Empty,
            FileName = dto.FileName ?? string.Empty,
            CapturedAt = dto.CapturedAt ?? string.Empty,
        };
    }

    private static CgObject FromDto(CgObjectDto dto)
    {
        return new CgObject
        {
            Name = dto.Name ?? string.Empty,
            ClassIri = dto.ClassIri,
            Source = dto.Source ?? "tagged",
            DgId = dto.DgId,
        };
    }

    private static CgAlgorithm FromDto(CgAlgorithmDto dto)
    {
        var algorithm = new CgAlgorithm
        {
            Index = dto.Index,
            Name = dto.Name ?? string.Empty,
        };

        foreach (var procedureDto in dto.Procedures ?? Enumerable.Empty<CgProcedureDto>())
        {
            algorithm.Procedures.Add(FromDto(procedureDto));
        }

        return algorithm;
    }

    private static CgProcedure FromDto(CgProcedureDto dto)
    {
        var procedure = new CgProcedure
        {
            Id = dto.Id ?? string.Empty,
            Index = dto.Index,
            Name = dto.Name ?? string.Empty,
            Source = dto.Source ?? "tagged",
            DgId = dto.DgId,
        };

        foreach (var memberId in dto.MemberIds ?? Enumerable.Empty<string>())
        {
            procedure.MemberIds.Add(memberId);
        }

        foreach (var patternDto in dto.Patterns ?? Enumerable.Empty<CgPatternDto>())
        {
            procedure.Patterns.Add(FromDto(patternDto));
        }

        foreach (var parameterDto in dto.Parameters ?? Enumerable.Empty<CgParameterDto>())
        {
            procedure.Parameters.Add(FromDto(parameterDto));
        }

        foreach (var interfaceDto in dto.Interfaces ?? Enumerable.Empty<CgInterfaceDto>())
        {
            procedure.Interfaces.Add(FromDto(interfaceDto));
        }

        return procedure;
    }

    private static CgPattern FromDto(CgPatternDto dto)
    {
        var pattern = new CgPattern
        {
            Id = dto.Id ?? string.Empty,
            Label = dto.Label ?? string.Empty,
            Name = dto.Name,
            HostPatternId = dto.HostPatternId,
            Source = dto.Source ?? "tagged",
            DgId = dto.DgId,
        };

        foreach (var memberId in dto.MemberIds ?? Enumerable.Empty<string>())
        {
            pattern.MemberIds.Add(memberId);
        }

        return pattern;
    }

    private static CgParameter FromDto(CgParameterDto dto)
    {
        var parameter = new CgParameter
        {
            Id = dto.Id ?? string.Empty,
            Kind = ParamKindFromDto(dto.Kind),
            Name = dto.Name ?? string.Empty,
            DataType = dto.DataType is not null ? ParamDataTypeFromDto(dto.DataType) : null,
            Domain = dto.Domain is not null ? FromDto(dto.Domain) : null,
            Source = dto.Source ?? "tagged",
            DgId = dto.DgId,
        };

        foreach (var memberId in dto.MemberIds ?? Enumerable.Empty<string>())
        {
            parameter.MemberIds.Add(memberId);
        }

        return parameter;
    }

    private static SliderDomain FromDto(SliderDomainDto dto)
    {
        return new SliderDomain
        {
            Min = dto.Min,
            Max = dto.Max,
            Step = dto.Step,
        };
    }

    private static CgInterface FromDto(CgInterfaceDto dto)
    {
        var iface = new CgInterface
        {
            Id = dto.Id ?? string.Empty,
            Name = dto.Name ?? string.Empty,
            IfaceType = IfaceTypeFromDto(dto.IfaceType),
            Source = dto.Source ?? "tagged",
            DgId = dto.DgId,
        };

        foreach (var memberId in dto.MemberIds ?? Enumerable.Empty<string>())
        {
            iface.MemberIds.Add(memberId);
        }

        return iface;
    }

    private static CgNode FromDto(CgNodeDto dto)
    {
        return new CgNode
        {
            InstanceId = dto.InstanceId ?? string.Empty,
            ComponentGuid = dto.ComponentGuid ?? string.Empty,
            Name = dto.Name ?? string.Empty,
            Nickname = dto.Nickname ?? string.Empty,
            Position = dto.Position ?? new double[2],
            Slider = dto.Slider is not null ? FromDto(dto.Slider) : null,
            IsIntegerSlider = dto.IsIntegerSlider,
        };
    }

    private static CgWire FromDto(CgWireDto dto)
    {
        return new CgWire
        {
            FromNode = dto.FromNode ?? string.Empty,
            FromParam = dto.FromParam ?? string.Empty,
            ToNode = dto.ToNode ?? string.Empty,
            ToParam = dto.ToParam ?? string.Empty,
        };
    }

    private static CgUntagged FromDto(CgUntaggedDto dto)
    {
        var untagged = new CgUntagged();

        foreach (var nodeId in dto.NodeIds ?? Enumerable.Empty<string>())
        {
            untagged.NodeIds.Add(nodeId);
        }

        foreach (var groupDto in dto.Groups ?? Enumerable.Empty<CgUntaggedGroupDto>())
        {
            untagged.Groups.Add(FromDto(groupDto));
        }

        return untagged;
    }

    private static CgUntaggedGroup FromDto(CgUntaggedGroupDto dto)
    {
        var group = new CgUntaggedGroup
        {
            Nickname = dto.Nickname ?? string.Empty,
        };

        foreach (var memberId in dto.MemberIds ?? Enumerable.Empty<string>())
        {
            group.MemberIds.Add(memberId);
        }

        return group;
    }

    private static ParamKind ParamKindFromDto(string? value) => value switch
    {
        "Variable" => ParamKind.Variable,
        "Constant" => ParamKind.Constant,
        "Emergent" => ParamKind.Emergent,
        _ => throw new InvalidOperationException(
            $"Unsupported paramKind '{value ?? "null"}'. Allowed values are Variable, Constant, Emergent."),
    };

    private static ParamDataType ParamDataTypeFromDto(string? value) => value switch
    {
        "Float" => ParamDataType.Float,
        "Integer" => ParamDataType.Integer,
        "Text" => ParamDataType.Text,
        "Boolean" => ParamDataType.Boolean,
        "Geometry" => ParamDataType.Geometry,
        _ => throw new InvalidOperationException(
            $"Unsupported dataType '{value ?? "null"}'. Allowed values are Float, Integer, Text, Boolean, Geometry."),
    };

    private static IfaceType IfaceTypeFromDto(string? value) => value switch
    {
        "Input" => IfaceType.Input,
        "Output" => IfaceType.Output,
        _ => throw new InvalidOperationException(
            $"Unsupported ifaceType '{value ?? "null"}'. Allowed values are Input, Output."),
    };

    private sealed class CgContextDto
    {
        public string? SchemaVersion { get; init; }

        public string? Project { get; init; }

        public CgDefinitionDto? Definition { get; init; }

        public CgObjectDto? Object { get; init; }

        public List<CgAlgorithmDto>? Algorithms { get; init; }

        public CgUntaggedDto? Untagged { get; init; }

        public List<CgNodeDto>? Nodes { get; init; }

        public List<CgWireDto>? Wires { get; init; }

        public List<string>? Warnings { get; init; }
    }

    private sealed class CgDefinitionDto
    {
        public string? DocumentId { get; init; }

        public string? FileName { get; init; }

        public string? CapturedAt { get; init; }
    }

    private sealed class CgObjectDto
    {
        public string? Name { get; init; }

        public string? ClassIri { get; init; }

        public string? Source { get; init; }

        public string? DgId { get; init; }
    }

    private sealed class CgAlgorithmDto
    {
        public int Index { get; init; }

        public string? Name { get; init; }

        public List<CgProcedureDto>? Procedures { get; init; }
    }

    private sealed class CgProcedureDto
    {
        public string? Id { get; init; }

        public int Index { get; init; }

        public string? Name { get; init; }

        public string? Source { get; init; }

        public string? DgId { get; init; }

        public List<string>? MemberIds { get; init; }

        public List<CgPatternDto>? Patterns { get; init; }

        public List<CgParameterDto>? Parameters { get; init; }

        public List<CgInterfaceDto>? Interfaces { get; init; }
    }

    private sealed class CgPatternDto
    {
        public string? Id { get; init; }

        public string? Label { get; init; }

        public string? Name { get; init; }

        public string? HostPatternId { get; init; }

        public List<string>? MemberIds { get; init; }

        public string? Source { get; init; }

        public string? DgId { get; init; }
    }

    private sealed class CgParameterDto
    {
        public string? Id { get; init; }

        public string? Kind { get; init; }

        public string? Name { get; init; }

        public string? DataType { get; init; }

        public SliderDomainDto? Domain { get; init; }

        public List<string>? MemberIds { get; init; }

        public string? Source { get; init; }

        public string? DgId { get; init; }
    }

    private sealed class SliderDomainDto
    {
        public double Min { get; init; }

        public double Max { get; init; }

        public double Step { get; init; }
    }

    private sealed class CgInterfaceDto
    {
        public string? Id { get; init; }

        public string? Name { get; init; }

        public string? IfaceType { get; init; }

        public List<string>? MemberIds { get; init; }

        public string? Source { get; init; }

        public string? DgId { get; init; }
    }

    private sealed class CgNodeDto
    {
        public string? InstanceId { get; init; }

        public string? ComponentGuid { get; init; }

        public string? Name { get; init; }

        public string? Nickname { get; init; }

        public double[]? Position { get; init; }

        public SliderDomainDto? Slider { get; init; }

        public bool IsIntegerSlider { get; init; }
    }

    private sealed class CgWireDto
    {
        public string? FromNode { get; init; }

        public string? FromParam { get; init; }

        public string? ToNode { get; init; }

        public string? ToParam { get; init; }
    }

    private sealed class CgUntaggedDto
    {
        public List<string>? NodeIds { get; init; }

        public List<CgUntaggedGroupDto>? Groups { get; init; }
    }

    private sealed class CgUntaggedGroupDto
    {
        public string? Nickname { get; init; }

        public List<string>? MemberIds { get; init; }
    }
}
