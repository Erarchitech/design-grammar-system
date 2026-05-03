namespace DG.Core.Models;

public sealed class ValidationRunRecord
{
    public string RunId { get; init; } = string.Empty;

    public string Project { get; init; } = "default-project";

    public string Graph { get; init; } = "Metagraph";

    public DateTimeOffset CapturedAtUtc { get; init; }

    public List<string> RuleIds { get; } = new();

    public string? StatePayloadJson { get; init; }
}
