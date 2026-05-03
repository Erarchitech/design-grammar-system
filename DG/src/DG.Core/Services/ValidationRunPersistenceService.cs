using DG.Core.Models;
using DG.Core.Serialization;

namespace DG.Core.Services;

public sealed class ValidationRunPersistenceService
{
    public ValidationRunRecord AttachDesignState(ValidationRunRecord record, DesignStateSnapshot? state)
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
