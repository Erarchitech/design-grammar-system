using System;
using DG.Core.Models.Computgraph;
using DG.Core.Models.Identity;

namespace DG.Core.Services;

/// <summary>
/// Walks a parsed <see cref="CgContext"/> and stamps a deterministic, project-scoped
/// <see cref="DgId"/> onto every tagged ontological entity (Object, Procedure, Pattern,
/// Parameter, Interface). Uses <see cref="DgIdMintingService.Mint"/> with the entityKey
/// derivation contract locked for Phase 36: typed entities key from <c>entity.Id</c>, the
/// Object keys from <c>"obj:" + Name</c>.
///
/// This is a pure GH-free service (no Grasshopper SDK references). Untagged nodes and the
/// raw Node/Wire substrate are NOT assigned identities — only ontological tagged entities
/// carry identity per DGID-01.
/// </summary>
public static class CgContextDgIdAssigner
{
    /// <summary>
    /// Stamps a deterministic <see cref="DgId"/> onto every tagged entity in the context.
    /// Mutates the context in place (the entity models have settable <c>DgId</c> for this purpose).
    /// </summary>
    /// <param name="context">A parsed CgContext with tagged entities.</param>
    /// <param name="project">The project scope (folded into the hash input for cross-project isolation).</param>
    /// <exception cref="ArgumentNullException">When <paramref name="context"/> is null.</exception>
    /// <exception cref="InvalidOperationException">When <paramref name="context"/> has no Definition.DocumentId.</exception>
    public static void AssignDgIds(CgContext context, string project)
    {
        ArgumentNullException.ThrowIfNull(context);

        if (string.IsNullOrWhiteSpace(context.Definition.DocumentId))
        {
            throw new InvalidOperationException("Definition.DocumentId is required for DG ID minting.");
        }

        var definitionId = context.Definition.DocumentId;

        // Object (has Name, not Id — derive key from "obj:" + Name)
        if (context.Object is not null)
        {
            var objectKey = $"obj:{context.Object.Name}";
            context.Object.DgId = DgIdMintingService.Mint(project, definitionId, objectKey).Value;
        }

        // Algorithms → Procedures → Patterns / Parameters / Interfaces
        foreach (var algorithm in context.Algorithms)
        {
            foreach (var procedure in algorithm.Procedures)
            {
                procedure.DgId = DgIdMintingService.Mint(project, definitionId, procedure.Id).Value;

                foreach (var pattern in procedure.Patterns)
                {
                    pattern.DgId = DgIdMintingService.Mint(project, definitionId, pattern.Id).Value;
                }

                foreach (var parameter in procedure.Parameters)
                {
                    parameter.DgId = DgIdMintingService.Mint(project, definitionId, parameter.Id).Value;
                }

                foreach (var iface in procedure.Interfaces)
                {
                    iface.DgId = DgIdMintingService.Mint(project, definitionId, iface.Id).Value;
                }
            }
        }
    }
}
