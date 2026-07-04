using DG.Core.Models;

namespace DG.Tests;

public sealed class OntologyPropertyModelTests
{
    [Fact]
    public void ShouldCreateWithIriAndLabel()
    {
        var prop = new OntologyProperty
        {
            Iri = "dg:project",
            Label = "Project",
        };

        Assert.Equal("dg:project", prop.Iri);
        Assert.Equal("Project", prop.Label);
    }

    [Fact]
    public void ShouldHaveEmptyStringDefaults()
    {
        var prop = new OntologyProperty();

        Assert.Equal(string.Empty, prop.Iri);
        Assert.Equal(string.Empty, prop.Label);
    }

    [Fact]
    public void Iri_ShouldBeNonNullAfterInit()
    {
        var prop = new OntologyProperty { Iri = "dgv:ValidStatus" };

        Assert.NotNull(prop.Iri);
        Assert.Equal("dgv:ValidStatus", prop.Iri);
    }
}
