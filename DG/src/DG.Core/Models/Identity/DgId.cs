using System;

namespace DG.Core.Models.Identity;

/// <summary>
/// A deterministic, platform-neutral identity for Computgraph entities.
/// Wraps a durable dg:-prefixed string that is derived from project, definitionId, and cgId.
/// This identity remains stable across re-extractions and enables cross-platform binding in the registry.
/// </summary>
public readonly record struct DgId(string Value)
{
    /// <summary>
    /// Returns the underlying dgId string (e.g., "dg:XXXXXXXXXXXXXXXX").
    /// </summary>
    public override string ToString() => Value;
}
