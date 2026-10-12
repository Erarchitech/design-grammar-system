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

    // --- ShaclViolation template tests ---

    [Theory]
    [InlineData("violation", "Door width below minimum", "focus:Door_12", "Increase width to at least 900mm")]
    [InlineData("warning", "Room area unusually small", "focus:Room_04", "Verify the room area is intentional")]
    [InlineData("info", "Wall thickness not specified", "focus:Wall_09", "Consider adding an explicit thickness value")]
    public void ShaclViolation_EachSeverity_ProducesHouseStyleMessage(string severity, string what, string where, string howToFix)
    {
        var result = ErrorMessageTemplates.ShaclViolation(severity, what, where, howToFix);

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains(severity, result);
        Assert.Contains(what, result);
        Assert.Contains(where, result);
        Assert.Contains(howToFix, result);
        Assert.Contains(": ", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ShaclViolation_HowToFixAlreadyEndingInPeriod_DoesNotDoublePunctuate()
    {
        var result = ErrorMessageTemplates.ShaclViolation(
            "violation",
            "Door width below minimum",
            "focus:Door_12",
            "Increase width to at least 900mm.");

        Assert.NotNull(result);
        Assert.EndsWith(".", result);
        Assert.DoesNotContain("..", result);
    }

    // --- Object-vs-Geometry list-length guard (Phase 1202-11, CR-02 / gap 2) ---

    [Theory]
    [InlineData(5, 0, false)]  // no Object wired — exempt
    [InlineData(5, 1, false)]  // broadcast case — exempt
    [InlineData(5, 5, false)]  // matched per-instance — exempt
    [InlineData(5, 3, true)]   // under-supply — mismatch
    [InlineData(5, 7, true)]   // over-supply — mismatch (tail entries would be silently ignored)
    [InlineData(0, 0, false)]  // no geometry, no objects — exempt
    [InlineData(1, 1, false)]  // broadcast and matched coincide — must not report a mismatch
    [InlineData(0, 3, true)]   // no geometry but objects wired — mismatch
    public void ObjStateGuard_IsObjectListLengthMismatch_MatchesExpectedShape(int geometryCount, int objectCount, bool expectedMismatch)
    {
        var result = ObjStateGuard.IsObjectListLengthMismatch(geometryCount, objectCount);

        Assert.Equal(expectedMismatch, result);
    }

    [Fact]
    public void ObjStateMismatchedObjectListLength_NamesObjectNotLabel()
    {
        var result = ErrorMessageTemplates.ObjStateMismatchedObjectListLength(5, 3);

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("OBJECT STATE", result);
        Assert.Contains("Object", result);
        Assert.Contains("5", result);
        Assert.Contains("3", result);
        Assert.DoesNotContain("Label", result);
    }

    [Fact]
    public void ObjStateMismatchedListLengths_UnchangedByThisPlan_StillLabelWorded()
    {
        // Pins the existing Label-side template byte-for-byte, proving Task 1 did not disturb it.
        var result = ErrorMessageTemplates.ObjStateMismatchedListLengths(5, 3);

        Assert.Equal(
            "OBJECT STATE: Geometry list length (5) and Label list length (3) must be equal at every index. Ensure each index provides both values.",
            result);
    }

    // --- Publish-auth template tests (Phase 1205-03, D-04/D-19) ---

    [Fact]
    public void PublishTokenMissing_NamesComponentAndTokenInput()
    {
        var result = ErrorMessageTemplates.PublishTokenMissing("VALIDATOR");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("VALIDATOR", result);
        Assert.Contains("Token input", result);
        Assert.Contains("CONNECTOR.Session", result);
        Assert.Contains("connector session", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishTokenMalformed_NamesDgkSessionAndIsDistinctFromMissing()
    {
        var result = ErrorMessageTemplates.PublishTokenMalformed("VALIDATOR");

        Assert.Contains("VALIDATOR", result);
        Assert.Contains("dgk_", result);
        Assert.Contains("CONNECTOR.Session", result);
        Assert.NotEqual(ErrorMessageTemplates.PublishTokenMissing("VALIDATOR"), result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishInsecureTransport_WarnsAboutPlainHttp()
    {
        var result = ErrorMessageTemplates.PublishInsecureTransport("COMPUTGRAPH PUBLISH");

        Assert.Contains("COMPUTGRAPH PUBLISH", result);
        Assert.Contains("plain http", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishTokenRejected_TellsToSignInAgainInConnector()
    {
        var result = ErrorMessageTemplates.PublishTokenRejected("COMPUTGRAPH PUBLISH");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("COMPUTGRAPH PUBLISH", result);
        Assert.Contains("rejected", result);
        Assert.Contains("Sign in again", result, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("CONNECTOR.Session", result);
        Assert.DoesNotContain("Mint a new token", result);
        Assert.DoesNotContain("Connectors screen", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishProjectForbidden_MentionsDifferentProjectAndSigningInAgain()
    {
        var result = ErrorMessageTemplates.PublishProjectForbidden("VALIDATOR");

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("VALIDATOR", result);
        Assert.Contains("different project", result);
        Assert.Contains("Sign in again", result, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("Connectors screen", result);
        Assert.EndsWith(".", result);
    }

    // --- Connector sign-in template tests (Phase 1308-04, D-35) ---

    [Fact]
    public void ConnectorSignInMissing_AsksForAccountCredentials()
    {
        var result = ErrorMessageTemplates.ConnectorSignInMissing();

        Assert.Contains("CONNECTOR", result);
        Assert.Contains("Username and Password", result);
        Assert.Contains("Connect=true", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ConnectorSignInRejected_SaysCredentialsWrong()
    {
        var result = ErrorMessageTemplates.ConnectorSignInRejected();

        Assert.Contains("CONNECTOR", result);
        Assert.Contains("rejected", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ConnectorSignInForbidden_DistinguishesProjectFromConnectorAccess()
    {
        var access = ErrorMessageTemplates.ConnectorSignInForbidden("CONNECTOR_ACCESS_REQUIRED");
        var project = ErrorMessageTemplates.ConnectorSignInForbidden("PROJECT_FORBIDDEN");
        var unknown = ErrorMessageTemplates.ConnectorSignInForbidden(null);

        Assert.Contains("grant connector access", access);
        Assert.Contains("Connectors screen", access);
        Assert.Contains("no access to that project", project);
        Assert.NotEqual(access, project);
        Assert.Equal(access, unknown);
        Assert.EndsWith(".", access);
        Assert.EndsWith(".", project);
    }

    [Fact]
    public void ConnectorProjectRequired_AppendsServerHint()
    {
        var withHint = ErrorMessageTemplates.ConnectorProjectRequired("Eligible projects: alpha, beta.");
        var without = ErrorMessageTemplates.ConnectorProjectRequired(null);

        Assert.Contains("Eligible projects: alpha, beta", withHint);
        Assert.DoesNotContain("..", withHint);
        Assert.EndsWith(".", withHint);
        Assert.Contains("Project input", without);
        Assert.EndsWith(".", without);
    }

    [Fact]
    public void ConnectorSignInThrottled_AsksToWait()
    {
        var result = ErrorMessageTemplates.ConnectorSignInThrottled();

        Assert.Contains("CONNECTOR", result);
        Assert.Contains("Wait", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ConnectorSignInInsecureTransport_IncludesUrlAndSaysNoPasswordSent()
    {
        var result = ErrorMessageTemplates.ConnectorSignInInsecureTransport("http://dg.example.com:8000");

        Assert.Contains("http://dg.example.com:8000", result);
        Assert.Contains("no password was sent", result);
        Assert.Contains("https", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void ConnectorSignInUnreachable_IncludesUrl()
    {
        var result = ErrorMessageTemplates.ConnectorSignInUnreachable("http://localhost:8000");

        Assert.Contains("CONNECTOR", result);
        Assert.Contains("http://localhost:8000", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void NoPublishOrSignInTemplate_MentionsRetiredTokenFlow()
    {
        var templates = new[]
        {
            ErrorMessageTemplates.PublishTokenMissing("VALIDATOR"),
            ErrorMessageTemplates.PublishTokenMalformed("VALIDATOR"),
            ErrorMessageTemplates.PublishInsecureTransport("VALIDATOR"),
            ErrorMessageTemplates.PublishTokenRejected("VALIDATOR"),
            ErrorMessageTemplates.PublishProjectForbidden("VALIDATOR"),
            ErrorMessageTemplates.ConnectorNoGraphBundle(),
            ErrorMessageTemplates.ConnectorSignInMissing(),
            ErrorMessageTemplates.ConnectorSignInRejected(),
            ErrorMessageTemplates.ConnectorSignInForbidden("PROJECT_FORBIDDEN"),
            ErrorMessageTemplates.ConnectorProjectRequired("hint"),
            ErrorMessageTemplates.ConnectorSignInThrottled(),
            ErrorMessageTemplates.ConnectorSignInInsecureTransport("http://h"),
            ErrorMessageTemplates.ConnectorSignInUnreachable("http://h"),
        };

        foreach (var text in templates)
        {
            Assert.DoesNotContain("dgc_", text);
            Assert.DoesNotContain("Mint a new token", text);
        }
    }

    [Fact]
    public void ConnectorNoGraphBundle_MentionsDirectBoltUnsupported()
    {
        var result = ErrorMessageTemplates.ConnectorNoGraphBundle();

        Assert.NotNull(result);
        Assert.NotEmpty(result);
        Assert.Contains("CONNECTOR", result);
        Assert.Contains("direct graph connection", result);
        Assert.Contains("Bolt", result);
        Assert.EndsWith(".", result);
    }

    [Fact]
    public void PublishAuthTemplates_NeverLeakARealTokenValue()
    {
        // The four templates are static text (no token parameter) — this asserts
        // none of them contains anything beyond the bare "dgk_" prefix hint, i.e.
        // no template accidentally interpolates an actual token value.
        var templates = new[]
        {
            ErrorMessageTemplates.PublishTokenMissing("VALIDATOR"),
            ErrorMessageTemplates.PublishTokenMalformed("VALIDATOR"),
            ErrorMessageTemplates.PublishInsecureTransport("VALIDATOR"),
            ErrorMessageTemplates.PublishTokenRejected("VALIDATOR"),
            ErrorMessageTemplates.PublishProjectForbidden("VALIDATOR"),
            ErrorMessageTemplates.ConnectorNoGraphBundle(),
        };

        foreach (var text in templates)
        {
            var idx = text.IndexOf("dgk_", StringComparison.Ordinal);
            if (idx < 0)
            {
                continue;
            }

            var afterPrefix = text.Substring(idx + "dgk_".Length);
            // Only an ellipsis or a space (the hint) may immediately follow;
            // a real token would continue alphanumerically.
            Assert.True(
                afterPrefix.Length == 0 || !char.IsLetterOrDigit(afterPrefix[0]),
                $"Template appears to embed a token value after the dgk_ prefix: '{text}'");
        }
    }
}
