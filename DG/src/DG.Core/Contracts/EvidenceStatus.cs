namespace DG.Core.Contracts;

/// <summary>
/// The frozen 8-member canonical status vocabulary (spec/EVIDENCE-CONTRACT.md section 1, D-02).
/// spec/EVIDENCE-CONTRACT.md is the semantic authority for what each member asserts;
/// spec/evidence-contract.schema.json <c>$defs.CanonicalStatus.enum</c> is the shape authority for
/// the exact wire-form literal set (per D-01, schema wins for shape, prose wins for meaning).
/// The wire form is lower snake_case and lives exclusively in <see cref="EvidenceStatusNames"/> —
/// this enum itself carries no wire-form information.
/// </summary>
public enum EvidenceStatus
{
    Passed,
    Failed,
    Unknown,
    NotEvaluated,
    NoPopulation,
    Unsupported,
    Indeterminate,
    Error,
}
