using DG.Core.Models;

namespace DG.Core.Data;

public sealed class ValidGraphQueryResult
{
    public IReadOnlyList<RunInfo> Runs { get; init; } = Array.Empty<RunInfo>();
    public IReadOnlyList<IReadOnlyList<bool>> StatusList { get; init; } = Array.Empty<IReadOnlyList<bool>>();
    public IReadOnlyList<DesignState> DesignStates { get; init; } = Array.Empty<DesignState>();
}

public class RunInfo
{
    public string RunId { get; init; } = string.Empty;
    public string Project { get; init; } = string.Empty;
    public DateTimeOffset CapturedAtUtc { get; init; }
    public IReadOnlyList<string> RuleIds { get; init; } = Array.Empty<string>();
    public string? StateId { get; init; }
}

public interface IValidGraphRepository
{
    Task<ValidGraphQueryResult> GetRunsAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);
}
