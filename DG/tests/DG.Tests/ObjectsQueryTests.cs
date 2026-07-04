using System.Reflection;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class ObjectsQueryTests
{
    private static string GetObjectsQueryConstant()
    {
        var field = typeof(Neo4jRuleRepository).GetField("ObjectsQuery", BindingFlags.NonPublic | BindingFlags.Static);
        Assert.NotNull(field);
        return (field!.GetValue(null) as string)!;
    }

    [Fact]
    public void ObjectsQuery_ShouldContainDedupKeyword()
    {
        var query = GetObjectsQueryConstant();

        Assert.Contains("DISTINCT", query);
    }

    [Fact]
    public void ObjectsQuery_ShouldTargetMetagraphLayer()
    {
        var query = GetObjectsQueryConstant();

        Assert.Contains("graph:'Metagraph'", query);
        Assert.Contains("$project", query);
    }

    [Fact]
    public void ObjectsQuery_ShouldReturnIriAndLabel()
    {
        var query = GetObjectsQueryConstant();

        Assert.Contains("c.iri AS iri", query);
        Assert.Contains("c.label AS label", query);
    }

    [Fact]
    public void ObjectsQuery_ShouldOrderByLabel()
    {
        var query = GetObjectsQueryConstant();

        Assert.Contains("ORDER BY c.label", query);
    }

    [Fact]
    public void ObjectsQuery_ShouldTraverseReferstoClass()
    {
        var query = GetObjectsQueryConstant();

        Assert.Contains("REFERS_TO", query);
        Assert.Contains("(c:Class)", query);
    }

    [Fact]
    public void OntologyClassModel_FromGetObjectsAsync_ShouldPreserveFields()
    {
        var obj = new OntologyClass
        {
            Iri = "http://example.com/Building",
            Label = "Building",
        };

        Assert.Equal("http://example.com/Building", obj.Iri);
        Assert.Equal("Building", obj.Label);
    }

    [Fact]
    public void OntologyClassModel_ShouldHaveEmptyStringDefaults()
    {
        var obj = new OntologyClass();

        Assert.Equal(string.Empty, obj.Iri);
        Assert.Equal(string.Empty, obj.Label);
    }
}
