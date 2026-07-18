namespace DG.Core.Models;

public class ObjState
{
    public string StateId { get; init; } = string.Empty;

    public string ObjectRef { get; init; } = string.Empty;

    public object? Geometry { get; init; }

    public string? Label { get; init; }

    /// <summary>
    /// The Class IRI of the ontology class this ObjState is an instance of.
    /// Set by OBJECT STATE from METAGRAPH Objects output.
    /// Used by DesignStateBindingService for Class IRI matching per D-05.
    /// </summary>
    public string? ClassIri { get; init; }

    public DateTimeOffset CapturedAtUtc { get; init; }

    /// <summary>
    /// Deterministic DG identity referencing the corresponding Computgraph entity.
    /// Set by the DesignStateDgIdAssigner (Plan 06); null before assignment.
    /// </summary>
    public string? DgId { get; init; }
}
