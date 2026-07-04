using System.Reflection;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class Neo4jOntoGraphRepositoryTests
{
    [Fact]
    public void ClassesQuery_ShouldTargetOntoGraphLayer()
    {
        var query = GetPrivateConst("ClassesQuery");
        Assert.Contains("graph:'OntoGraph'", query);
        Assert.Contains("project:$project", query);
    }

    [Fact]
    public void ClassesQuery_ShouldMatchClassLabel()
    {
        var query = GetPrivateConst("ClassesQuery");
        Assert.Contains("(c:Class", query);
        Assert.Contains("c.iri AS iri", query);
        Assert.Contains("c.label AS label", query);
    }

    [Fact]
    public void ObjPropertiesQuery_ShouldUseV7Name()
    {
        var query = GetPrivateConst("ObjPropertiesQuery");
        Assert.Contains("(p:ObjProperty", query);
        Assert.Contains("graph:'OntoGraph'", query);
    }

    [Fact]
    public void DataPropertiesQuery_ShouldUseV7Name()
    {
        var query = GetPrivateConst("DataPropertiesQuery");
        Assert.Contains("(p:DataProperty", query);
        Assert.Contains("graph:'OntoGraph'", query);
    }

    [Fact]
    public void AllQueries_ShouldOrderByLabel()
    {
        var classesQuery = GetPrivateConst("ClassesQuery");
        var objPropsQuery = GetPrivateConst("ObjPropertiesQuery");
        var dataPropsQuery = GetPrivateConst("DataPropertiesQuery");

        Assert.All(new[] { classesQuery, objPropsQuery, dataPropsQuery },
            query => Assert.Contains("ORDER BY", query));
    }

    [Fact]
    public void AllQueries_ShouldBeParameterized()
    {
        var classesQuery = GetPrivateConst("ClassesQuery");
        var objPropsQuery = GetPrivateConst("ObjPropertiesQuery");
        var dataPropsQuery = GetPrivateConst("DataPropertiesQuery");

        Assert.All(new[] { classesQuery, objPropsQuery, dataPropsQuery },
            query => Assert.Contains("$project", query));
    }

    [Fact]
    public void Repository_ShouldImplementInterface()
    {
        var repo = new Neo4jOntoGraphRepository();
        Assert.IsAssignableFrom<IOntoGraphRepository>(repo);
    }

    [Fact]
    public void OntologyPropertyModel_ShouldPreserveFields()
    {
        var prop = new OntologyProperty
        {
            Iri = "http://example.com/hasHeight",
            Label = "hasHeight",
        };

        Assert.Equal("http://example.com/hasHeight", prop.Iri);
        Assert.Equal("hasHeight", prop.Label);
    }

    [Fact]
    public void OntologyPropertyModel_ShouldHaveEmptyStringDefaults()
    {
        var prop = new OntologyProperty();
        Assert.Equal(string.Empty, prop.Iri);
        Assert.Equal(string.Empty, prop.Label);
    }

    private static string GetPrivateConst(string fieldName)
    {
        var field = typeof(Neo4jOntoGraphRepository)
            .GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Static);
        Assert.NotNull(field);
        return (field!.GetValue(null) as string) ?? string.Empty;
    }
}
