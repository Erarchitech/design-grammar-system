using DG.Core.Models;

namespace DG.Core.Data;

public interface IRuleRepository
{
    Task<IReadOnlyList<Rule>> GetRulesAsync(ConnectionInfo connection, CancellationToken cancellationToken = default);
}
