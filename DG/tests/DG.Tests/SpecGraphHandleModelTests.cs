using DG.Core.Models;

namespace DG.Tests;

public sealed class SpecGraphHandleModelTests
{
    [Fact]
    public void DefaultConnectionInfo_ShouldNotBeNull()
    {
        var handle = new SpecGraphHandle();

        Assert.NotNull(handle.ConnectionInfo);
    }

    [Fact]
    public void ShouldSetConnectionInfo_ThroughInit()
    {
        var connection = new ConnectionInfo
        {
            Uri = "bolt://test:7687",
            User = "test-user",
            Password = "test-pass",
            Database = "test-db",
            Project = "test-project",
        };

        var handle = new SpecGraphHandle { ConnectionInfo = connection };

        Assert.Equal("bolt://test:7687", handle.ConnectionInfo.Uri);
        Assert.Equal("test-user", handle.ConnectionInfo.User);
        Assert.Equal("test-pass", handle.ConnectionInfo.Password);
        Assert.Equal("test-db", handle.ConnectionInfo.Database);
        Assert.Equal("test-project", handle.ConnectionInfo.Project);
    }

    [Fact]
    public void ShouldWrapSameConnectionInfoReference()
    {
        var connection = new ConnectionInfo
        {
            Uri = "bolt://ref-test:7687",
            User = "ref-user",
            Password = "ref-pass",
            Database = "ref-db",
            Project = "ref-project",
        };

        var handle = new SpecGraphHandle { ConnectionInfo = connection };

        Assert.Same(connection, handle.ConnectionInfo);
    }
}
