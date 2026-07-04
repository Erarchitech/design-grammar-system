using DG.Core.Models;

namespace DG.Core.Data;

public interface IOntoGraphRepository
{
    Task<IReadOnlyList<OntologyClass>> GetClassesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<OntologyProperty>> GetObjPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<OntologyProperty>> GetDataPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);
}
