using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace DG.Core.Contracts;

/// <summary>
/// Per-(rule, object) evidence row (spec/EVIDENCE-CONTRACT.md sections 3/4;
/// spec/evidence-contract.schema.json <c>$defs.EvidenceRow</c>). Rows are addressed by the
/// (<see cref="RuleId"/>, <see cref="ObjectId"/>) identity pair — two value-equal rows with
/// distinct identity remain separately addressable and are never merged, collided, or
/// deduplicated on value equality alone. Property names carry <see cref="JsonPropertyNameAttribute"/>
/// so the schema's exact camelCase field names are produced, matching the shape the DE-01 runner
/// validates against.
/// </summary>
public sealed class EvidenceRow
{
    [JsonPropertyName("ruleId")]
    public string RuleId { get; init; } = string.Empty;

    [JsonPropertyName("objectId")]
    public string ObjectId { get; init; } = string.Empty;

    [JsonPropertyName("canonicalStatus")]
    [JsonConverter(typeof(EvidenceStatusJsonConverter))]
    public EvidenceStatus CanonicalStatus { get; init; }

    [JsonPropertyName("warnings")]
    public List<string>? Warnings { get; init; }

    [JsonPropertyName("inputHash")]
    public string? InputHash { get; init; }

    [JsonPropertyName("outputHash")]
    public string? OutputHash { get; init; }

    [JsonPropertyName("detail")]
    public string? Detail { get; init; }
}

/// <summary>
/// The evidence envelope a stage emits to report the outcome of evaluating one or more rules
/// against a design (spec/EVIDENCE-CONTRACT.md section 3, D-06; spec/evidence-contract.schema.json
/// <c>$defs.EvidenceEnvelope</c>). Property names mirror the schema's field names exactly via
/// <see cref="JsonPropertyNameAttribute"/> so C#-emitted JSON validates against the same schema
/// the Python leg validates against. Emitted at every stage boundary that produces or transforms
/// a verdict, not only at final persistence.
/// </summary>
public sealed class EvidenceEnvelope
{
    [JsonPropertyName("contractVersion")]
    public string ContractVersion { get; init; } = string.Empty;

    [JsonPropertyName("canonicalizationVersion")]
    public int CanonicalizationVersion { get; init; }

    [JsonPropertyName("project")]
    public string Project { get; init; } = string.Empty;

    [JsonPropertyName("definitionId")]
    public string DefinitionId { get; init; } = string.Empty;

    [JsonPropertyName("serviceName")]
    public string ServiceName { get; init; } = string.Empty;

    [JsonPropertyName("serviceVersion")]
    public string ServiceVersion { get; init; } = string.Empty;

    [JsonPropertyName("emittedAt")]
    public string EmittedAt { get; init; } = string.Empty;

    [JsonPropertyName("stage")]
    public string Stage { get; init; } = string.Empty;

    [JsonPropertyName("canonicalStatus")]
    [JsonConverter(typeof(EvidenceStatusJsonConverter))]
    public EvidenceStatus CanonicalStatus { get; init; }

    [JsonPropertyName("rows")]
    public List<EvidenceRow> Rows { get; init; } = new();

    [JsonPropertyName("dgId")]
    public string? DgId { get; init; }

    [JsonPropertyName("sourceRepresentation")]
    public object? SourceRepresentation { get; init; }

    [JsonPropertyName("inputHash")]
    public string? InputHash { get; init; }

    [JsonPropertyName("outputHash")]
    public string? OutputHash { get; init; }

    [JsonPropertyName("schemaVersion")]
    public string? SchemaVersion { get; init; }

    [JsonPropertyName("ontologyVersion")]
    public string? OntologyVersion { get; init; }

    [JsonPropertyName("ruleVersion")]
    public string? RuleVersion { get; init; }

    [JsonPropertyName("shapeVersion")]
    public string? ShapeVersion { get; init; }

    [JsonPropertyName("provider")]
    public string? Provider { get; init; }

    [JsonPropertyName("model")]
    public string? Model { get; init; }

    [JsonPropertyName("warnings")]
    public List<string>? Warnings { get; init; }
}
