using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ErrorMessageTemplateTests
{
    [Theory]
    [InlineData(SerializationError.NoStateProvided)]
    [InlineData(SerializationError.MalformedStatePayload)]
    [InlineData(SerializationError.MissingParameterId)]
    [InlineData(SerializationError.TimestampMissing)]
    public void SerializationFailed_EachEnumValue_ProducesTemplatedMessage(SerializationError error)
    {
        var result = ErrorMessageTemplates.SerializationFailed("height", error);

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("height", result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Theory]
    [InlineData(ReinstatementStatus.MissingTarget)]
    [InlineData(ReinstatementStatus.TypeMismatch)]
    [InlineData(ReinstatementStatus.AmbiguousTarget)]
    [InlineData(ReinstatementStatus.OutOfRange)]
    public void ReinstatementBlocked_EachBlockingStatus_ProducesActionableMessage(ReinstatementStatus status)
    {
        var result = ErrorMessageTemplates.ReinstatementBlocked("wallHeight", status, "Boolean in state but Slider is Number");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("wallHeight", result);
        Assert.Contains("Boolean in state but Slider is Number", result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ValidationInputMissing_ReturnsFormattedMessage()
    {
        var result = ErrorMessageTemplates.ValidationInputMissing("Rules");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("Rules", result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishFailed_IncludesProjectAndDetail()
    {
        var result = ErrorMessageTemplates.PublishFailed("project-x", "connection refused");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("project-x", result);
        Assert.Contains("connection refused", result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void DesignStateTypeUnsupported_IncludesParameterAndType()
    {
        var result = ErrorMessageTemplates.DesignStateTypeUnsupported("myParam", "GH_Curve");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("myParam", result);
        Assert.Contains("GH_Curve", result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void AllMethods_ReturnNonEmpty()
    {
        Assert.NotEmpty(ErrorMessageTemplates.SerializationFailed("p", SerializationError.NoStateProvided));
        Assert.NotEmpty(ErrorMessageTemplates.ReinstatementBlocked("p", ReinstatementStatus.MissingTarget, "d"));
        Assert.NotEmpty(ErrorMessageTemplates.ValidationInputMissing("X"));
        Assert.NotEmpty(ErrorMessageTemplates.PublishFailed("proj", "err"));
        Assert.NotEmpty(ErrorMessageTemplates.DesignStateTypeUnsupported("p", "T"));
    }
}
