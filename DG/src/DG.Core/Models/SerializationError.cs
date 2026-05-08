namespace DG.Core.Models;

public enum SerializationError
{
    NoStateProvided,
    MalformedStatePayload,
    MissingParameterId,
    TimestampMissing,
}
