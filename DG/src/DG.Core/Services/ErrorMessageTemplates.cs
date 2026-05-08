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
}
