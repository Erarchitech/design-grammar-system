using DG.Core.Models;
using DG.Core.Serialization;

namespace DG.Core.Services;

public sealed class ValidationRunPersistenceService
{
    public ValidationRunRecord AttachDesignState(ValidationRunRecord record, ParamState? state)
    {
        if (state is null)
        {
            return record;
        }

        try
        {
            var serialized = DesignStateJsonSerializer.Serialize(state);
            return new ValidationRunRecord
            {
                RunId = record.RunId,
                Project = record.Project,
                Graph = record.Graph,
                CapturedAtUtc = record.CapturedAtUtc,
                StatePayloadJson = serialized,
            };
        }
        catch (InvalidOperationException ex)
        {
            throw new InvalidOperationException("Failed to serialize design state for validation run persistence.", ex);
        }
    }

    /// <summary>
    /// Attaches a v2 DesignState payload to a validation run record.
    /// Uses DesignStatePayloadV2Serializer for serialization.
    /// </summary>
    public ValidationRunRecord AttachDesignStateV2(ValidationRunRecord record, DesignState? designState)
    {
        if (designState is null)
        {
            return record;
        }

        try
        {
            var serialized = DesignStatePayloadV2Serializer.Serialize(designState);
            return new ValidationRunRecord
            {
                RunId = record.RunId,
                Project = record.Project,
                Graph = record.Graph,
                CapturedAtUtc = record.CapturedAtUtc,
                StatePayloadJson = serialized,
            };
        }
        catch (InvalidOperationException ex)
        {
            throw new InvalidOperationException("Failed to serialize v2 design state for validation run persistence.", ex);
        }
    }

    /// <summary>
    /// Validates a StatePayloadJson string by auto-detecting v1 vs v2 format.
    /// v2 payloads contain "version":"2"; v1 payloads use DesignStateJsonSerializer format.
    /// </summary>
    public void ValidateDesignStatePayload(string? statePayloadJson)
    {
        if (string.IsNullOrWhiteSpace(statePayloadJson))
            return;

        try
        {
            if (statePayloadJson.Contains("\"version\":\"2\"", StringComparison.Ordinal))
            {
                DesignStatePayloadV2Serializer.Deserialize(statePayloadJson);
            }
            else
            {
                DesignStateJsonSerializer.Deserialize(statePayloadJson);
            }
        }
        catch (InvalidOperationException ex)
        {
            throw new InvalidOperationException("StatePayloadJson is not valid design state payload.", ex);
        }
    }

    public void ValidateRunRecord(ValidationRunRecord record)
    {
        if (string.IsNullOrWhiteSpace(record.RunId))
        {
            throw new InvalidOperationException("RunId is required for validation run record.");
        }

        if (string.IsNullOrWhiteSpace(record.Project))
        {
            throw new InvalidOperationException("Project is required for validation run record.");
        }

        if (record.CapturedAtUtc == default)
        {
            throw new InvalidOperationException("CapturedAtUtc is required for validation run record.");
        }

        if (!string.IsNullOrWhiteSpace(record.StatePayloadJson))
        {
            try
            {
                DesignStateJsonSerializer.Deserialize(record.StatePayloadJson);
            }
            catch (InvalidOperationException ex)
            {
                throw new InvalidOperationException("StatePayloadJson is not a valid design state snapshot.", ex);
            }
        }
    }
}
