using System;
using System.Security.Cryptography;
using System.Text;

namespace DG.Core.Models.Identity;

/// <summary>
/// Deterministic, platform-neutral minting of <see cref="DgId"/> identities for Computgraph entities.
/// The hash-input domain is exactly <c>project|definitionId|cgId</c> (pipe-joined, in that order):
/// folding <c>project</c> into the input closes the v2.0 cross-project Var collision class, and the
/// determinism makes re-extraction stability free — no persistence round-trip is required to "remember"
/// an entity's identity.
///
/// The <c>dg:</c> prefix is domain-unique and MUST NOT collide with the
/// <c>DS_/OS_/PS_/IDR_</c> prefixes minted by <see cref="DG.Core.Services.DesignStateIdGenerator"/>.
///
/// The <see cref="HashToHex16"/> helper is a verbatim byte-identical copy of
/// <c>DesignStateIdGenerator.HashToHex16</c> — duplicated (not shared) to preserve the repo's
/// no-cross-file-coupling convention. Any change to the hash-input contract here breaks cross-platform
/// identity parity with the data-service <c>compute_dg_id</c> implementation and is guarded by the
/// golden-vector test.
/// </summary>
public static class DgIdMintingService
{
    private const string DgIdPrefix = "dg:";

    /// <summary>
    /// Mints a deterministic <see cref="DgId"/> from the pipe-joined triple
    /// <c>project|definitionId|cgId</c>. Identical inputs always produce a byte-identical dgId;
    /// differing <c>project</c> values for the same definitionId+cgId produce distinct dgIds.
    /// </summary>
    public static DgId Mint(string project, string definitionId, string cgId)
    {
        if (string.IsNullOrWhiteSpace(project))
            throw new ArgumentException("project must be a non-empty value.", nameof(project));
        if (string.IsNullOrWhiteSpace(definitionId))
            throw new ArgumentException("definitionId must be a non-empty value.", nameof(definitionId));
        if (string.IsNullOrWhiteSpace(cgId))
            throw new ArgumentException("cgId must be a non-empty value.", nameof(cgId));

        var input = $"{project}|{definitionId}|{cgId}";
        return new DgId(DgIdPrefix + HashToHex16(input));
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
