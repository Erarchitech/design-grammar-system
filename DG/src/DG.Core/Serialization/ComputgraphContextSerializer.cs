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
