using DG.Core.Models;
using DG.Core.Services;
using DG.Core.Serialization;

namespace DG.Tests;

public sealed class ValidationRunPersistenceTests
{
    [Fact]
    public void AttachDesignState_WhenStateIsValid_ShouldSerializeAndAttach()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };
        record.RuleIds.Add("R_HEIGHT");

        var state = new DesignStateSnapshot
        {
            StateId = "state-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T09:30:00.0000000Z"),
        };
        state.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.5,
        });

        var recordWithState = service.AttachDesignState(record, state);

        Assert.NotNull(recordWithState.StatePayloadJson);
        Assert.Contains("state-1", recordWithState.StatePayloadJson);
        Assert.Contains("height", recordWithState.StatePayloadJson);
    }

    [Fact]
    public void AttachDesignState_WhenStateIsNull_ShouldReturnRecordUnchanged()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };

        var recordWithoutState = service.AttachDesignState(record, null);

        Assert.Null(recordWithoutState.StatePayloadJson);
        Assert.Equal("run-1", recordWithoutState.RunId);
    }

    [Fact]
    public void AttachDesignState_WhenStateSerializationFails_ShouldThrow()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };

        var invalidState = new DesignStateSnapshot
        {
            StateId = "state-1",
            CapturedAtUtc = default,
        };

        var ex = Assert.Throws<InvalidOperationException>(() => service.AttachDesignState(record, invalidState));
        Assert.Contains("serialize", ex.Message);
    }

    [Fact]
    public void ValidateRunRecord_WhenAllFieldsValid_ShouldNotThrow()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };
        record.RuleIds.Add("R_HEIGHT");

        service.ValidateRunRecord(record);
    }

    [Fact]
    public void ValidateRunRecord_WhenRunIdMissing_ShouldThrow()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = string.Empty,
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };

        var ex = Assert.Throws<InvalidOperationException>(() => service.ValidateRunRecord(record));
        Assert.Contains("RunId", ex.Message);
    }

    [Fact]
    public void ValidateRunRecord_WhenCapturedAtUtcMissing_ShouldThrow()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = default,
        };

        var ex = Assert.Throws<InvalidOperationException>(() => service.ValidateRunRecord(record));
        Assert.Contains("CapturedAtUtc", ex.Message);
    }

    [Fact]
    public void ValidateRunRecord_WhenStatePayloadIsInvalidJson_ShouldThrow()
    {
        var service = new ValidationRunPersistenceService();
        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
            StatePayloadJson = "{ invalid json",
        };

        var ex = Assert.Throws<InvalidOperationException>(() => service.ValidateRunRecord(record));
        Assert.Contains("design state", ex.Message);
    }

    [Fact]
    public void ValidateRunRecord_WhenStatePayloadIsValidJson_ShouldNotThrow()
    {
        var service = new ValidationRunPersistenceService();
        var snapshot = new DesignStateSnapshot
        {
            StateId = "state-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T09:30:00.0000000Z"),
        };
        snapshot.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.5,
        });
        var serialized = DesignStateJsonSerializer.Serialize(snapshot);

        var record = new ValidationRunRecord
        {
            RunId = "run-1",
            Project = "project-a",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
            StatePayloadJson = serialized,
        };

        service.ValidateRunRecord(record);
    }
}
