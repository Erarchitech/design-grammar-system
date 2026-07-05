using DG.Core.Models;

namespace DG.Core.Services;

public static class ErrorMessageTemplates
{
    public static string SerializationFailed(string parameterId, SerializationError error)
    {
        return error switch
        {
            SerializationError.NoStateProvided =>
                $"State capture failed: no state provided for parameter '{parameterId}'. Connect a DESIGN STATE component upstream.",
            SerializationError.MalformedStatePayload =>
                $"State serialization failed: parameter '{parameterId}' produced invalid payload. Disconnect and reconnect the parameter input.",
            SerializationError.MissingParameterId =>
                $"State capture incomplete: parameter '{parameterId}' has no identifier. Right-click the input and set a NickName.",
            SerializationError.TimestampMissing =>
                $"State capture failed: parameter '{parameterId}' has no timestamp. Re-capture the design state.",
            _ =>
                $"State error: parameter '{parameterId}' encountered an unknown error. Re-capture the design state.",
        };
    }

    public static string ReinstatementBlocked(string parameterId, ReinstatementStatus status, string detail)
    {
        var fix = status switch
        {
            ReinstatementStatus.MissingTarget => "Reconnect the original slider or toggle.",
            ReinstatementStatus.TypeMismatch => "Reconnect a matching slider or recapture state.",
            ReinstatementStatus.AmbiguousTarget => "Ensure only one slider has this NickName.",
            ReinstatementStatus.OutOfRange => "Adjust slider domain to include the saved value.",
            _ => "Check the parameter connection.",
        };

        return $"Reinstatement blocked: parameter '{parameterId}' {detail}. {fix}";
    }

    public static string ValidationInputMissing(string inputName)
    {
        return $"Validation input missing: {inputName} is required. Connect {inputName} to the component input.";
    }

    public static string PublishFailed(string project, string errorDetail)
    {
        return $"Validation publish failed for project '{project}': {errorDetail}. Check data-service connection and Speckle configuration.";
    }

    public static string DesignStateTypeUnsupported(string parameterName, string typeName)
    {
        return $"Design state capture skipped: parameter '{parameterName}' has unsupported type '{typeName}'. Only Number, Integer, and Boolean inputs are supported.";
    }

    public static string ObjStateMismatchedListLengths(int objectCount, int geometryCount, int labelCount, int classCount)
    {
        return $"OBJECT STATE: Object list length ({objectCount}), Geometry list length ({geometryCount}), Label list length ({labelCount}), and Class list length ({classCount}) must be equal at every index. Ensure each index provides all four values per D-03.";
    }

    public static string PropStateMismatchedListLengths(int ruleCount, int dataPropertyCount, int propValueCount)
    {
        return $"PROPERTY STATE: Rule list length ({ruleCount}), DataProperty list length ({dataPropertyCount}), and PropValue list length ({propValueCount}) must be equal at every index. Ensure each index provides all three values per D-03.";
    }

    public static string DesignStateNoInputs()
    {
        return "DESIGN STATE: At least one ObjState, ParamState, or PropState input must contain items. Wire at least one upstream state component.";
    }

    public static string GraphDeconstructNoInput()
    {
        return "GRAPH DECONSTRUCT: Database input is required. Connect a CONNECTOR component to the Database input.";
    }

    public static string GraphDeconstructCastFailed()
    {
        return "GRAPH DECONSTRUCT: Could not cast Database input. Ensure the input is connected to a CONNECTOR component.";
    }

    public static string ConnectorProjectPassthroughFailed()
    {
        return "CONNECTOR: Project output passthrough failed. Ensure PROJECT NAME input is connected.";
    }

    public static string RuleVariableUnclassified(string ruleId, string variableName)
    {
        return $"Cannot classify variable '?{variableName}' in rule '{ruleId}': no REFERS_TO link found. Ensure the SWRL expression assigns every variable to a ClassAtom, DataPropertyAtom, or ObjectPropertyAtom. Re-ingest the rule through the rules-ingest webhook.";
    }

    public static string BindingServiceNoObjectBindings(string ruleId)
    {
        return $"Binding service for rule '{ruleId}': DesignState contains no ObjStates but the rule requires Object variables. Connect OBJECT STATE components upstream to supply building instances for validation.";
    }

    public static string HandleTypeUnwrapped(string componentName, string handleType)
    {
        return $"{componentName}: Could not unwrap {handleType} input. Ensure the input is connected to GRAPH DECONSTRUCT's {handleType} output.";
    }

    // --- Deconstruct templates (DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT) ---

    public static string DesignStateDeconstructInputMissing()
    {
        return "DESIGN STATE DECONSTRUCT: DesignState input is required. Connect a DESIGN STATE or VALIDATION GRAPH component to the DesignState input.";
    }

    public static string DesignStateDeconstructCastFailed()
    {
        return "DESIGN STATE DECONSTRUCT: Could not unwrap the DesignState input. Ensure the input is connected to a DESIGN STATE or VALIDATION GRAPH component.";
    }

    public static string ObjectDeconstructInputMissing()
    {
        return "OBJECT DECONSTRUCT: ObjState input is required. Connect a DESIGN STATE DECONSTRUCT or OBJECT STATE component to the ObjState input.";
    }

    public static string ObjectDeconstructCastFailed()
    {
        return "OBJECT DECONSTRUCT: Could not unwrap the ObjState input. Ensure the input is connected to a DESIGN STATE DECONSTRUCT or OBJECT STATE component.";
    }

    // --- Reinstate templates (PARAMETER REINSTATE) ---

    public static string ReinstateTargetRequired()
    {
        return "PARAMETER REINSTATE: Target input is required. Wire the 'State' output of a PARAMETER STATE component to the Target input.";
    }

    public static string ReinstateSourceNotFound()
    {
        return "PARAMETER REINSTATE: Could not find a PARAMETER STATE component upstream of the Target input. Ensure the Target input is wired to a PARAMETER STATE component's State output.";
    }

    // --- Format helpers (moved from old ReinstateComponent) ---

    public static string FormatStatus(ReinstatementResult result)
    {
        if (result.Applied)
            return result.AppliedCount > 0
                ? $"Applied {result.AppliedCount} parameters"
                : "Applied (0)";

        if (result.Aborted)
            return result.BlockedCount > 0
                ? $"Aborted: {result.BlockedCount} blocked"
                : "Aborted (0)";

        if (result.UnchangedCount > 0)
            return "Unchanged (same state)";

        return "Idle";
    }

    public static string FormatMessage(ReinstatementResult result)
    {
        if (result.Applied)
            return result.AppliedCount > 0
                ? $"Applied {result.AppliedCount}"
                : "Applied";

        if (result.Aborted)
            return result.BlockedCount > 0
                ? "Aborted"
                : "Aborted";

        if (result.UnchangedCount > 0)
            return "Unchanged";

        return "Idle";
    }
}
