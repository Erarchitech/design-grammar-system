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
    /// </summary>
    [Fact]
    public void Mint_KnownVector_MatchesExpectedDgId()
    {
        var dgId = DgIdMintingService.Mint("p1", "frame.gh", "cg:1:proc:11_Proc");

        Assert.Equal("dg:BC8E62EE137E2B56", dgId.Value);
    }
}
