using System.Text.RegularExpressions;
using DG.Core.Models.Identity;

namespace DG.Tests;

/// <summary>
/// Proves the deterministic-minting half of DGID-01: re-extraction stability, cross-project
/// isolation, rename re-mint semantics, dg-prefixed 16-hex format, and a cross-language golden vector.
/// </summary>
public sealed class DgIdMintingServiceTests
{
    private const string Project = "p1";
    private const string DefinitionId = "frame.gh";
    private const string CgId = "cg:1:proc:11_Proc";

    [Fact]
    public void Mint_SameInputsTwice_ProducesIdenticalDgId()
    {
        var first = DgIdMintingService.Mint(Project, DefinitionId, CgId);
        var second = DgIdMintingService.Mint(Project, DefinitionId, CgId);

        Assert.Equal(first, second);
    }

    [Fact]
    public void Mint_DifferentProjectsSameEntity_ProducesDifferentDgId()
    {
        var p1 = DgIdMintingService.Mint("p1", DefinitionId, CgId);
        var p2 = DgIdMintingService.Mint("p2", DefinitionId, CgId);

        Assert.NotEqual(p1, p2);
    }

    [Fact]
    public void Mint_RenamedConventionGroup_ReMintsDifferentDgId()
    {
        var original = DgIdMintingService.Mint(Project, DefinitionId, "cg:1:var:11_Var_SpansCount");
        var renamed = DgIdMintingService.Mint(Project, DefinitionId, "cg:1:var:11_Var_Count");

        Assert.NotEqual(original, renamed);
    }

    [Fact]
    public void Mint_Always_ReturnsDgPrefixedSixteenHex()
    {
        var dgId = DgIdMintingService.Mint(Project, DefinitionId, CgId);

        Assert.StartsWith("dg:", dgId.Value);
        var remainder = dgId.Value["dg:".Length..];
        Assert.Equal(16, remainder.Length);
        Assert.Matches(new Regex("^[0-9A-F]{16}$"), remainder);
    }

    /// <summary>
    /// Golden vector — data-service compute_dg_id (Plan 03 / test_dg_identity.py) MUST reproduce
    /// this exact input→output pair; changing the hash input contract breaks cross-platform identity.
    /// Input triple: project "p1", definitionId "frame.gh", cgId "cg:1:proc:11_Proc".
    ///
    /// Re-derived Phase 1203-02 (D-09 length-prefix encoding replaces the naive pipe-join): the
    /// pre-fix value was "dg:BC8E62EE137E2B56"; this is the post-fix value under the final
    /// EncodeHashInput contract. data-service/tests/test_dg_identity.py's GOLDEN_DG_ID and
    /// data-service/tests/test_computgraph_publish.py's GOLDEN_DG_ID were updated to the same
    /// value in the same commit.
    /// </summary>
    [Fact]
    public void Mint_KnownVector_MatchesExpectedDgId()
    {
        var dgId = DgIdMintingService.Mint("p1", "frame.gh", "cg:1:proc:11_Proc");

        Assert.Equal("dg:0F31CD18542F0252", dgId.Value);
    }

    /// <summary>
    /// CR-02 collision regression: two distinct input tuples that share the SAME naive
    /// pipe-join ("a|b|c|d") must mint DIFFERENT dgIds once the hash input is length-prefixed.
    ///
    /// Tuple A = ("a|b", "c", "d") and tuple B = ("a", "b|c", "d") both naively join to
    /// "a|b|c|d" — under the pre-fix implementation (var input = $"{project}|{definitionId}|{cgId}")
    /// these two calls would hash the identical string and therefore collide (this.Equal, not
    /// this.NotEqual). Under the length-prefix encoding, A encodes to "3:a|b|1:c|1:d" and B
    /// encodes to "1:a|3:b|c|1:d" — different strings, different hashes. This test only passes
    /// against the length-prefix fix; it fails against the naive-join implementation it replaces.
    /// </summary>
    [Fact]
    public void Mint_PipeBoundaryShift_ProducesDifferentDgId()
    {
        var a = DgIdMintingService.Mint("a|b", "c", "d");
        var b = DgIdMintingService.Mint("a", "b|c", "d");

        Assert.NotEqual(a, b);
    }
}
