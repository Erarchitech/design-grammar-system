using DG.Core.Models;

namespace DG.Tests;

public sealed class OntologyClassModelTests
{
    [Fact]
    public void ShouldCreateWithIriAndLabel()
    {
        var cls = new OntologyClass
        {
            Iri = "dgm:Rule",
            Label = "Rule",
        };

        Assert.Equal("dgm:Rule", cls.Iri);
        Assert.Equal("Rule", cls.Label);
    }

    [Fact]
    public void ShouldHaveEmptyStringDefaults()
    {
        var cls = new OntologyClass();

        Assert.Equal(string.Empty, cls.Iri);
        Assert.Equal(string.Empty, cls.Label);
    }

    [Fact]
    public void Iri_ShouldBeNonNullAfterInit()
    {
        var cls = new OntologyClass { Iri = "dg:Object" };

        Assert.NotNull(cls.Iri);
        Assert.Equal("dg:Object", cls.Iri);
    }
}
