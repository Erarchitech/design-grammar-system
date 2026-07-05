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

    // --- Deconstruct template tests ---

    [Fact]
    public void DesignStateDeconstructInputMissing_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.DesignStateDeconstructInputMissing();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("DESIGN STATE DECONSTRUCT", result);
        Assert.Contains("DesignState input is required", result);
        Assert.Contains("CONNECT", result, StringComparison.OrdinalIgnoreCase);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void DesignStateDeconstructCastFailed_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.DesignStateDeconstructCastFailed();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("DESIGN STATE DECONSTRUCT", result);
        Assert.Contains("Could not unwrap", result);
        Assert.Contains("DESIGN STATE or VALIDATION GRAPH", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ObjectDeconstructInputMissing_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.ObjectDeconstructInputMissing();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("OBJECT DECONSTRUCT", result);
        Assert.Contains("input is required", result);
        Assert.Contains("DESIGN STATE DECONSTRUCT or OBJECT STATE", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ObjectDeconstructCastFailed_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.ObjectDeconstructCastFailed();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("OBJECT DECONSTRUCT", result);
        Assert.Contains("Could not unwrap", result);
        Assert.Contains("DESIGN STATE DECONSTRUCT or OBJECT STATE", result);
        Assert.EndsWith(".", result);
    }

    // --- Reinstate template tests ---

    [Fact]
    public void ReinstateTargetRequired_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.ReinstateTargetRequired();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("PARAMETER REINSTATE", result);
        Assert.Contains("Target input is required", result);
        Assert.Contains("PARAMETER STATE", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ReinstateSourceNotFound_IncludesComponentAndActionAndFix()
    {
        var result = ErrorMessageTemplates.ReinstateSourceNotFound();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("PARAMETER REINSTATE", result);
        Assert.Contains("Could not find", result);
        Assert.Contains("PARAMETER STATE", result);
        Assert.EndsWith(".", result);
    }

    // --- FormatStatus tests ---

    [Fact]
    public void FormatStatus_AppliedWithCount_ReturnsAppliedSummary()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Applied },
            new() { ParameterId = "w", DisplayName = "width", Status = ReinstatementStatus.Applied },
        };
        var result = new ReinstatementResult
        {
            Applied = true,
            Aborted = false,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatStatus(result);

        Assert.Equal("Applied 2 parameters", output);
    }

    [Fact]
    public void FormatStatus_AbortedWithBlocked_ReturnsAbortedSummary()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.MissingTarget },
            new() { ParameterId = "w", DisplayName = "width", Status = ReinstatementStatus.TypeMismatch },
        };
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = true,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatStatus(result);

        Assert.Equal("Aborted: 2 blocked", output);
    }

    [Fact]
    public void FormatStatus_Unchanged_ReturnsUnchangedSummary()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Unchanged },
        };
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatStatus(result);

        Assert.Equal("Unchanged (same state)", output);
    }

    [Fact]
    public void FormatStatus_Idle_ReturnsIdle()
    {
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>(),
        };

        var output = ErrorMessageTemplates.FormatStatus(result);

        Assert.Equal("Idle", output);
    }

    // --- FormatMessage tests ---

    [Fact]
    public void FormatMessage_AppliedWithCount_ReturnsAppliedMessage()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Applied },
        };
        var result = new ReinstatementResult
        {
            Applied = true,
            Aborted = false,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatMessage(result);

        Assert.Equal("Applied 1", output);
    }

    [Fact]
    public void FormatMessage_Aborted_ReturnsAbortedMessage()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.MissingTarget },
        };
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = true,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatMessage(result);

        Assert.Equal("Aborted", output);
    }

    [Fact]
    public void FormatMessage_Unchanged_ReturnsUnchangedMessage()
    {
        var reports = new List<ReinstatementParameterReport>
        {
            new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Unchanged },
        };
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = reports,
        };

        var output = ErrorMessageTemplates.FormatMessage(result);

        Assert.Equal("Unchanged", output);
    }

    [Fact]
    public void FormatMessage_Idle_ReturnsIdle()
    {
        var result = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>(),
        };

        var output = ErrorMessageTemplates.FormatMessage(result);

        Assert.Equal("Idle", output);
    }

    [Fact]
    public void AllNewMethods_ReturnNonEmpty()
    {
        Assert.NotEmpty(ErrorMessageTemplates.DesignStateDeconstructInputMissing());
        Assert.NotEmpty(ErrorMessageTemplates.DesignStateDeconstructCastFailed());
        Assert.NotEmpty(ErrorMessageTemplates.ObjectDeconstructInputMissing());
        Assert.NotEmpty(ErrorMessageTemplates.ObjectDeconstructCastFailed());
        Assert.NotEmpty(ErrorMessageTemplates.ReinstateTargetRequired());
        Assert.NotEmpty(ErrorMessageTemplates.ReinstateSourceNotFound());

        var idleResult = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>(),
        };
        Assert.NotEmpty(ErrorMessageTemplates.FormatStatus(idleResult));
        Assert.NotEmpty(ErrorMessageTemplates.FormatMessage(idleResult));
    }
}
