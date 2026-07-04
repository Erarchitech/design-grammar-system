using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ConnectorComponentPortContractTests
{
    [Fact]
    public void ErrorMessage_GraphDeconstructNoInput_ReturnsExpectedFormat()
    {
        var message = ErrorMessageTemplates.GraphDeconstructNoInput();

        Assert.Contains("GRAPH DECONSTRUCT", message);
        Assert.Contains("Database input is required", message);
        Assert.Contains("CONNECTOR", message);
    }

    [Fact]
    public void ErrorMessage_GraphDeconstructCastFailed_ReturnsExpectedFormat()
    {
        var message = ErrorMessageTemplates.GraphDeconstructCastFailed();

        Assert.Contains("GRAPH DECONSTRUCT", message);
        Assert.Contains("Could not cast Database input", message);
        Assert.Contains("CONNECTOR", message);
    }

    [Fact]
    public void ErrorMessage_ConnectorProjectPassthroughFailed_ReturnsExpectedFormat()
    {
        var message = ErrorMessageTemplates.ConnectorProjectPassthroughFailed();

        Assert.Contains("CONNECTOR", message);
        Assert.Contains("Project output passthrough failed", message);
        Assert.Contains("PROJECT NAME", message);
    }

    [Fact]
    public void ErrorMessage_HandleTypeUnwrapped_ReturnsExpectedFormat()
    {
        var message = ErrorMessageTemplates.HandleTypeUnwrapped("METAGRAPH", "Metagraph");

        Assert.Contains("METAGRAPH", message);
        Assert.Contains("Could not unwrap Metagraph input", message);
        Assert.Contains("GRAPH DECONSTRUCT", message);
        Assert.Contains("Metagraph", message);
    }

    [Fact]
    public void HandleType_MetagraphHandle_ExistsInCore()
    {
        var handle = new MetagraphHandle();

        Assert.NotNull(handle);
        Assert.NotNull(handle.ConnectionInfo);
    }

    [Fact]
    public void HandleType_OntographHandle_ExistsInCore()
    {
        var handle = new OntographHandle();

        Assert.NotNull(handle);
        Assert.NotNull(handle.ConnectionInfo);
    }

    [Fact]
    public void HandleType_ValidGraphHandle_ExistsInCore()
    {
        var handle = new ValidGraphHandle();

        Assert.NotNull(handle);
        Assert.NotNull(handle.ConnectionInfo);
    }

    [Fact]
    public void HandleType_SpecGraphHandle_ExistsInCore()
    {
        var handle = new SpecGraphHandle();

        Assert.NotNull(handle);
        Assert.NotNull(handle.ConnectionInfo);
    }
}
