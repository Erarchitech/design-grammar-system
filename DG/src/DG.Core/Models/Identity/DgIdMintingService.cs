using System;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace DG.Core.Models.Identity;

/// <summary>
/// Deterministic, platform-neutral minting of <see cref="DgId"/> identities for Computgraph entities.
/// The hash-input domain is the ordered triple <c>(project, definitionId, cgId)</c>, combined via
/// <see cref="EncodeHashInput"/> (length-prefixed, not a naive pipe-join — D-09/CR-02): folding
/// <c>project</c> into the input closes the v2.0 cross-project Var collision class, and the
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
    /// Mints a deterministic <see cref="DgId"/> from the length-prefix-encoded triple
    /// <c>(project, definitionId, cgId)</c> (see <see cref="EncodeHashInput"/>). Identical inputs
    /// always produce a byte-identical dgId; differing <c>project</c> values for the same
    /// definitionId+cgId produce distinct dgIds.
    /// </summary>
    public static DgId Mint(string project, string definitionId, string cgId)
    {
        if (string.IsNullOrWhiteSpace(project))
            throw new ArgumentException("project must be a non-empty value.", nameof(project));
        if (string.IsNullOrWhiteSpace(definitionId))
            throw new ArgumentException("definitionId must be a non-empty value.", nameof(definitionId));
        if (string.IsNullOrWhiteSpace(cgId))
            throw new ArgumentException("cgId must be a non-empty value.", nameof(cgId));

        var input = EncodeHashInput(project, definitionId, cgId);
        return new DgId(DgIdPrefix + HashToHex16(input));
    }

    /// <summary>
    /// Encodes an ordered tuple of optional string components into a single hash-input string
    /// with an unambiguous component boundary — the D-09 / CR-02 fix.
    ///
    /// <para>
    /// <b>Rule (twinned verbatim with <see cref="DG.Core.Services.DesignStateIdGenerator"/>'s own
    /// copy of this rule, and with Python <c>dg_identity._encode_hash_input</c>):</b> for each
    /// component, in order, emit the component's character length in invariant decimal, then a
    /// colon, then the component's raw text; join the resulting units with a single pipe. A
    /// <c>null</c> component emits the literal unit <c>-1:</c> (no trailing text); an empty-string
    /// component emits <c>0:</c>. Because every unit is preceded by an unambiguous length, a pipe
    /// (or any other character) inside a component's raw text can never be mistaken for a
    /// component boundary, closing the pipe-collision class CR-02 identifies in the naive
    /// pipe-join this helper replaces.
    /// </para>
    /// <para>
    /// Length is counted in UTF-16 characters (<c>string.Length</c>), not bytes, and the integer
    /// is formatted with <see cref="CultureInfo.InvariantCulture"/> so a non-English host locale
    /// cannot change the digit glyphs or grouping.
    /// </para>
    /// </summary>
    private static string EncodeHashInput(params string?[] components)
    {
        var sb = new StringBuilder();
        for (var i = 0; i < components.Length; i++)
        {
            if (i > 0)
            {
                sb.Append('|');
            }

            var component = components[i];
            if (component is null)
            {
                sb.Append("-1:");
            }
            else
            {
                sb.Append(component.Length.ToString(CultureInfo.InvariantCulture));
                sb.Append(':');
                sb.Append(component);
            }
        }

        return sb.ToString();
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
