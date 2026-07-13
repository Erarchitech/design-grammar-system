namespace DG.Core.Models;

/// <summary>
/// Neo4j connection details unlocked by an authenticated platform token
/// (Phase 825, CONNG-03). Returned by the data-service heartbeat so the
/// CONNECTOR component derives its whole connection from the token alone —
/// no URI/User/Password/Database/Project inputs on the canvas.
///
/// Token-free by construction: the raw token never enters this record.
/// </summary>
public readonly record struct ConnectionBundle(
    string? Uri,
    string? User,
    string? Password,
    string? Database,
    string? Project);
