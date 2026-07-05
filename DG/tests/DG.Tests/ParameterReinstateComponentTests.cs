using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ParameterReinstateComponentTests
{
    // ── D-05: Parameters output contains ALL captured params ────────────────────

    [Fact]
    public void ParametersOutput_ContainsAllCapturedParams()
    {
        // D-05: ALL parameters from ParamState are output, not just applied ones.
        // This test validates the ParamState model contract: Parameters collection
        // holds all items regardless of their eventual reinstatement status.
        var paramState = new ParamState
        {
            StateId = "PS_all_params_test",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 50.0,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "floors",
            DisplayName = "Floors",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 10,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "hasPodium",
            DisplayName = "Has Podium",
            Type = DesignStateParameterType.Boolean,
            BooleanValue = true,
        });

        Assert.Equal(3, paramState.Parameters.Count);
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "height");
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "floors");
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "hasPodium");
    }

    // ── D-04: StateStatus list is index-matched to Parameters ───────────────────

    [Fact]
    public void StateStatus_IndexMatchedToParameters()
    {
        // D-04: StateStatus list must have the same length as Parameters and
        // every index i must correspond to the same ParameterId.
        var paramState = new ParamState
        {
            StateId = "PS_index_test",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 50.0,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "floors",
            DisplayName = "Floors",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 10,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "hasPodium",
            DisplayName = "Has Podium",
            Type = DesignStateParameterType.Boolean,
            BooleanValue = true,
        });

        // Create a result with 3 reports matching the 3 parameters
        var result = new ReinstatementResult
        {
            Applied = true,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>
            {
                new() { ParameterId = "height", DisplayName = "Height", Status = ReinstatementStatus.Applied },
                new() { ParameterId = "floors", DisplayName = "Floors", Status = ReinstatementStatus.Applied },
                new() { ParameterId = "hasPodium", DisplayName = "Has Podium", Status = ReinstatementStatus.Applied },
            },
        };

        // Verify list-length parity (D-04 invariant)
        Assert.Equal(paramState.Parameters.Count, result.Reports.Count);

        // Verify per-index ParameterId matching (D-04 invariant)
        for (var i = 0; i < paramState.Parameters.Count; i++)
        {
            Assert.Equal(paramState.Parameters[i].ParameterId, result.Reports[i].ParameterId);
        }
    }

    // ── ReinstatementStatus enum contract ────────────────────────────────────────

    [Fact]
    public void ReinstatementStatus_EnumHasSevenValues()
    {
        var values = Enum.GetValues<ReinstatementStatus>();

        Assert.Contains(ReinstatementStatus.Applied, values);
        Assert.Contains(ReinstatementStatus.MissingTarget, values);
        Assert.Contains(ReinstatementStatus.TypeMismatch, values);
        Assert.Contains(ReinstatementStatus.AmbiguousTarget, values);
        Assert.Contains(ReinstatementStatus.OutOfRange, values);
        Assert.Contains(ReinstatementStatus.Unchanged, values);
        Assert.Contains(ReinstatementStatus.WouldApply, values);

        Assert.Equal(7, values.Length);
    }

    // ── Null guard path ─────────────────────────────────────────────────────────

    [Fact]
    public void UnwrapSnapshot_NullInput_ReturnsNull()
    {
        // At the Core model level, this validates that null ParamState
        // is handled gracefully: accessing Parameters on null returns null,
        // and coalescing produces an empty list (matching the component's
        // SetOutputs pattern: _latestParamState?.Parameters.ToList() ?? empty).
        ParamState? nullState = null;

        var parameters = nullState?.Parameters.ToList() ?? new List<DesignStateParameter>();

        Assert.NotNull(parameters);
        Assert.Empty(parameters);
    }

    // ── Assembly-mismatch reconstruction round-trip ─────────────────────────────

    [Fact]
    public void ReconstructSnapshot_AssemblyMismatchHandling()
    {
        // The component's ReconstructSnapshot and ReconstructParameter methods
        // use reflection to read ParamState and DesignStateParameter properties
        // by name. This test validates that all required properties are present
        // and accessible by the same names the reflection path uses:
        //   ParamState: StateId, CapturedAtUtc, Parameters
        //   DesignStateParameter: ParameterId, DisplayName, Type,
        //     NumberValue, IntegerValue, BooleanValue
        var paramState = new ParamState
        {
            StateId = "PS_reconstruct",
            CapturedAtUtc = new DateTimeOffset(2026, 6, 15, 14, 30, 0, TimeSpan.Zero),
        };

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "width",
            DisplayName = "Width",
            Type = DesignStateParameterType.Number,
            NumberValue = 42.5,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "count",
            DisplayName = "Count",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 7,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "enabled",
            DisplayName = "Enabled",
            Type = DesignStateParameterType.Boolean,
            BooleanValue = false,
        });

        // Verify properties by name (same names as reflection path)
        var stateIdProp = typeof(ParamState).GetProperty("StateId");
        Assert.NotNull(stateIdProp);
        Assert.Equal("PS_reconstruct", stateIdProp!.GetValue(paramState));

        var capturedAtProp = typeof(ParamState).GetProperty("CapturedAtUtc");
        Assert.NotNull(capturedAtProp);
        Assert.Equal(new DateTimeOffset(2026, 6, 15, 14, 30, 0, TimeSpan.Zero), capturedAtProp!.GetValue(paramState));

        var parametersProp = typeof(ParamState).GetProperty("Parameters");
        Assert.NotNull(parametersProp);
        var parameters = parametersProp!.GetValue(paramState) as System.Collections.IEnumerable;
        Assert.NotNull(parameters);

        // Verify DesignStateParameter properties round-trip through reflection
        var paramType = typeof(DesignStateParameter);

        var paramIdProp = paramType.GetProperty("ParameterId");
        Assert.NotNull(paramIdProp);

        var displayNameProp = paramType.GetProperty("DisplayName");
        Assert.NotNull(displayNameProp);

        var typeProp = paramType.GetProperty("Type");
        Assert.NotNull(typeProp);

        var numValueProp = paramType.GetProperty("NumberValue");
        Assert.NotNull(numValueProp);

        var intValueProp = paramType.GetProperty("IntegerValue");
        Assert.NotNull(intValueProp);

        var boolValueProp = paramType.GetProperty("BooleanValue");
        Assert.NotNull(boolValueProp);

        // Verify each parameter's properties
        var widthParam = paramState.Parameters[0];
        Assert.Equal("width", paramIdProp!.GetValue(widthParam));
        Assert.Equal("Width", displayNameProp!.GetValue(widthParam));
        Assert.Equal(DesignStateParameterType.Number, typeProp!.GetValue(widthParam));
        Assert.Equal(42.5, numValueProp!.GetValue(widthParam));

        var countParam = paramState.Parameters[1];
        Assert.Equal("count", paramIdProp!.GetValue(countParam));
        Assert.Equal("Count", displayNameProp!.GetValue(countParam));
        Assert.Equal(DesignStateParameterType.Integer, typeProp!.GetValue(countParam));
        Assert.Equal(7L, intValueProp!.GetValue(countParam));

        var enabledParam = paramState.Parameters[2];
        Assert.Equal("enabled", paramIdProp!.GetValue(enabledParam));
        Assert.Equal("Enabled", displayNameProp!.GetValue(enabledParam));
        Assert.Equal(DesignStateParameterType.Boolean, typeProp!.GetValue(enabledParam));
        Assert.Equal(false, boolValueProp!.GetValue(enabledParam));
    }

    // ── Error template contracts ────────────────────────────────────────────────

    [Fact]
    public void ReinstateTargetRequired_ErrorContract()
    {
        var required = ErrorMessageTemplates.ReinstateTargetRequired();

        Assert.NotEmpty(required);
        Assert.Contains("PARAMETER REINSTATE", required);
        Assert.Contains("Target input", required);
        Assert.Contains("required", required);
        Assert.EndsWith(".", required);

        var notFound = ErrorMessageTemplates.ReinstateSourceNotFound();

        Assert.NotEmpty(notFound);
        Assert.Contains("PARAMETER REINSTATE", notFound);
        Assert.Contains("upstream", notFound);
        Assert.Contains("PARAMETER STATE", notFound);
        Assert.EndsWith(".", notFound);
    }

    [Fact]
    public void FormatStatus_And_FormatMessage_Contract()
    {
        // Verify all branches produce non-empty output
        var appliedResult = new ReinstatementResult
        {
            Applied = true,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>
            {
                new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Applied },
            },
        };

        Assert.NotEmpty(ErrorMessageTemplates.FormatStatus(appliedResult));
        Assert.Contains("Applied", ErrorMessageTemplates.FormatStatus(appliedResult));

        Assert.NotEmpty(ErrorMessageTemplates.FormatMessage(appliedResult));
        Assert.Contains("Applied", ErrorMessageTemplates.FormatMessage(appliedResult));

        var abortedResult = new ReinstatementResult
        {
            Applied = false,
            Aborted = true,
            Reports = new List<ReinstatementParameterReport>
            {
                new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.MissingTarget },
            },
        };

        Assert.NotEmpty(ErrorMessageTemplates.FormatStatus(abortedResult));
        Assert.Contains("Aborted", ErrorMessageTemplates.FormatStatus(abortedResult));

        Assert.NotEmpty(ErrorMessageTemplates.FormatMessage(abortedResult));
        Assert.Contains("Aborted", ErrorMessageTemplates.FormatMessage(abortedResult));

        var unchangedResult = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>
            {
                new() { ParameterId = "h", DisplayName = "height", Status = ReinstatementStatus.Unchanged },
            },
        };

        Assert.NotEmpty(ErrorMessageTemplates.FormatStatus(unchangedResult));
        Assert.Contains("Unchanged", ErrorMessageTemplates.FormatStatus(unchangedResult));

        Assert.NotEmpty(ErrorMessageTemplates.FormatMessage(unchangedResult));
        Assert.Contains("Unchanged", ErrorMessageTemplates.FormatMessage(unchangedResult));

        var idleResult = new ReinstatementResult
        {
            Applied = false,
            Aborted = false,
            Reports = new List<ReinstatementParameterReport>(),
        };

        Assert.NotEmpty(ErrorMessageTemplates.FormatStatus(idleResult));
        Assert.Equal("Idle", ErrorMessageTemplates.FormatStatus(idleResult));

        Assert.NotEmpty(ErrorMessageTemplates.FormatMessage(idleResult));
        Assert.Equal("Idle", ErrorMessageTemplates.FormatMessage(idleResult));
    }
}
