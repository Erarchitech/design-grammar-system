"""Cross-platform identity registry — dgId minting, native-id ↔ dgId resolution, binding.

Identity model
--------------
- ``dgId`` is the durable, platform-neutral anchor for a Computgraph entity. It is
  minted deterministically from ``project|definitionId|cgId`` (pipe-joined, in that
  exact order) via SHA-256 — no persistence round-trip is required to "remember" an
  entity's identity, and folding ``project`` into the hash closes the v2.0
  cross-project collision class.
- Native ids (a Grasshopper ``InstanceGuid``, a Revit ``UniqueId``, an IFC
  ``GlobalId`` …) are *representations* bound to a dgId. Counterpart objects across
  platforms therefore resolve to ONE identity (DGID-03).
- Every query is project-scoped: ``project`` is threaded as a bound parameter and is
  part of every MATCH/MERGE key — defense in depth on top of ``project`` already
  being folded into the dgId hash (DGID-05).

``compute_dg_id`` mirrors the C# ``DG.Core.Models.Identity.DgIdMintingService.Mint``
contract byte-for-byte: ``Convert.ToHexString`` in .NET yields UPPERCASE hex, so the
Python digest is uppercased before slicing the first 16 chars. A golden-vector test
guards this cross-language parity.

Two-layer error model (mirrors ``speckle_validation.SpeckleValidationError``): the
plain domain exception ``DgIdentityError`` is raised deep in these helpers and carries
a ``code`` attribute; ``app.py`` translates it into a structured HTTP error higher up.

Cross-phase seam (Phase 36 publish path)
----------------------------------------
``mint_identity`` upserts on the anchor key ``(cgId, definitionId, project)``. This is
the pre-mint anchor Phase 36's publish path lands on — Phase 36's publish MERGE key
MUST include ``cgId`` (alongside ``definitionId`` + ``project``, per its CGPD-02
contract) so pre-minted registry nodes and published Computgraph nodes COINCIDE rather
than duplicate.

Security: every ``session.run`` receives parameters as a dict — identity strings
(``native_id`` / ``dg_id`` / ``project`` / ``platform``) are NEVER f-string / ``%`` /
``.format`` interpolated into query text (T-32.1-03a: Cypher injection).
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, field_validator


# ── Minting contract (C# parity mirror) ──

DGID_PREFIX = "dg:"


def compute_dg_id(project: str, definition_id: str, cg_id: str) -> str:
    """Mint a deterministic dgId from the pipe-joined triple ``project|definitionId|cgId``.

    Byte-identical to DG.Core ``DgIdMintingService.Mint``: SHA-256 the UTF-8 input,
    render the digest as UPPERCASE hex (matching .NET ``Convert.ToHexString``), take
    the first 16 hex chars, and prefix with ``dg:``. Identical inputs always produce a
    byte-identical dgId; a differing ``project`` for the same definitionId+cgId yields a
    distinct dgId.
    """
    input_str = f"{project}|{definition_id}|{cg_id}"
    digest = hashlib.sha256(input_str.encode("utf-8")).hexdigest().upper()
    return DGID_PREFIX + digest[:16]


# ── Enumerations ──

PLATFORMS: tuple[str, ...] = ("Grasshopper", "Revit", "IFC", "Speckle")
NATIVE_ID_KINDS: tuple[str, ...] = ("InstanceGuid", "UniqueId", "GlobalId", "ApplicationId")


# ── Domain exception (translated to a structured HTTP error in app.py) ──


class DgIdentityError(Exception):
    """Domain error raised by the persistence helpers.

    Carries a ``code`` attribute (e.g. ``DGID_NOT_FOUND`` / ``DGID_AMBIGUOUS_BINDING``)
    that ``app.py`` maps to the matching structured HTTP response + status code.
    """

    def __init__(self, message: str, code: str = "DGID_ERROR"):
        super().__init__(message)
        self.code = code


# ── Pydantic request/response models ──


class MintRequest(BaseModel):
    """Body for POST /identity/mint."""

    project: str
    definition_id: str
    cg_id: str


class BindRepresentationRequest(BaseModel):
    """Body for POST /identity/bind — asserts a native-id ↔ dgId binding."""

    dg_id: str
    platform: str
    native_id_kind: str
    native_id: str
    connector: str
    project: str

    @field_validator("platform")
    @classmethod
    def _platform_known(cls, v: str) -> str:
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}, got {v!r}")
        return v

    @field_validator("native_id_kind")
    @classmethod
    def _kind_known(cls, v: str) -> str:
        if v not in NATIVE_ID_KINDS:
            raise ValueError(f"native_id_kind must be one of {NATIVE_ID_KINDS}, got {v!r}")
        return v


class RepresentationResponse(BaseModel):
    """One bound platform representation."""

    platform: str
    native_id_kind: str
    native_id: str
    connector: str
    bound_at: str | None = None


class ResolveResponse(BaseModel):
    """Response for a native-id → dgId resolution."""

    dg_id: str


# ── Persistence helpers ──
#
# Each takes a duck-typed `session` (real neo4j Session, or a FixtureSession in tests)
# as its first arg; app.py opens `with driver.session() as session:` and passes it.
# `op=…` trailing comments tag each query's role for the test fixture — harmless in
# real Cypher.


def mint_identity(session: Any, project: str, definition_id: str, cg_id: str) -> str:
    """Idempotently mint + persist a dgId for a Computgraph entity; return the dgId.

    Upserts on the anchor key ``(cgId, definitionId, project)`` and SETs ``dgId``.
    Re-minting the same triple yields the same dgId and does not duplicate the node.

    Cross-phase seam: Phase 36's publish MERGE key MUST include ``cgId`` (alongside
    ``definitionId`` + ``project``) so pre-minted registry nodes and published
    Computgraph nodes coincide rather than duplicate (see module docstring).
    """
    dg_id = compute_dg_id(project, definition_id, cg_id)
    session.run(
        """
        MERGE (e {cgId: $cgId, definitionId: $definitionId, project: $project})
        SET e.dgId = $dgId
        // op=MINT
        """,
        {
            "project": project,
            "definitionId": definition_id,
            "cgId": cg_id,
            "dgId": dg_id,
        },
    )
    return dg_id


def resolve_native_id(
    session: Any, platform: str, native_id: str, project: str
) -> str | None:
    """Resolve a (platform, native_id) representation to its owning entity's dgId.

    Project-scoped: returns the dgId of the entity that HAS_REPRESENTATION the given
    native id within ``project``, or ``None`` when no such binding exists.
    """
    result = session.run(
        """
        MATCH (e {project: $project})-[:HAS_REPRESENTATION]->(r:Representation {nativeId: $nativeId, platform: $platform, project: $project})
        RETURN e.dgId AS dgId
        // op=RESOLVE
        """,
        {"project": project, "platform": platform, "nativeId": native_id},
    )
    record = result.single()
    return record["dgId"] if record else None


def bind_representation(
    session: Any,
    dg_id: str,
    platform: str,
    native_id_kind: str,
    native_id: str,
    connector: str,
    project: str,
) -> dict:
    """Bind a native-id representation to a dgId — never a silent repoint.

    Anti-misbinding guard (T-32.1-03b): FIRST resolve any existing representation on
    ``(nativeId, platform, project)``; if it is already bound to a DIFFERENT dgId,
    raise ``DgIdentityError(DGID_AMBIGUOUS_BINDING)`` rather than a bare idempotent
    MERGE that would reassign identity. Then verify the target entity ``{dgId, project}``
    exists (``DGID_NOT_FOUND`` otherwise), then MERGE the Representation + HAS_REPRESENTATION
    edge.
    """
    existing = resolve_native_id(session, platform, native_id, project)
    if existing is not None and existing != dg_id:
        raise DgIdentityError(
            f"Native id '{native_id}' is already bound to dgId '{existing}'.",
            code="DGID_AMBIGUOUS_BINDING",
        )

    entity = session.run(
        """
        MATCH (e {dgId: $dgId, project: $project})
        RETURN e.dgId AS dgId
        LIMIT 1
        // op=ENTITY_CHECK
        """,
        {"dgId": dg_id, "project": project},
    ).single()
    if entity is None:
        raise DgIdentityError(
            f"No Computgraph entity found with dgId '{dg_id}'.",
            code="DGID_NOT_FOUND",
        )

    session.run(
        """
        MATCH (e {dgId: $dgId, project: $project})
        MERGE (r:Representation {nativeId: $nativeId, platform: $platform, project: $project})
        ON CREATE SET r.nativeIdKind = $nativeIdKind,
                      r.connector = $connector,
                      r.boundAt = datetime(),
                      r.graph = 'Computgraph'
        MERGE (e)-[:HAS_REPRESENTATION]->(r)
        // op=BIND
        """,
        {
            "dgId": dg_id,
            "platform": platform,
            "nativeId": native_id,
            "nativeIdKind": native_id_kind,
            "connector": connector,
            "project": project,
        },
    )
    return {
        "platform": platform,
        "native_id_kind": native_id_kind,
        "native_id": native_id,
        "connector": connector,
        "dg_id": dg_id,
    }


def list_representations(session: Any, dg_id: str, project: str) -> list[dict]:
    """List all platform representations bound to a dgId within a project."""
    result = session.run(
        """
        MATCH (e {dgId: $dgId, project: $project})-[:HAS_REPRESENTATION]->(r:Representation {project: $project})
        RETURN r.platform AS platform,
               r.nativeIdKind AS native_id_kind,
               r.nativeId AS native_id,
               r.connector AS connector,
               toString(r.boundAt) AS bound_at
        // op=LIST
        """,
        {"dgId": dg_id, "project": project},
    )
    return [
        {
            "platform": rec["platform"],
            "native_id_kind": rec["native_id_kind"],
            "native_id": rec["native_id"],
            "connector": rec["connector"],
            "bound_at": rec["bound_at"],
        }
        for rec in result
    ]


def detach_representation(
    session: Any, dg_id: str, platform: str, native_id: str, project: str
) -> bool:
    """Detach a representation — deletes ONLY the Representation node and its edge.

    DGID-02 detach clause: the DETACH DELETE statement performs NO write on the entity
    ``e``, so the dgId is untouched; the freed ``(nativeId, platform, project)`` triple
    then has no existing-binding row and is re-bindable afterward (to the same or a
    different dgId). Raises ``DgIdentityError(DGID_NOT_FOUND)`` when no such binding
    exists.
    """
    count_row = session.run(
        """
        MATCH (e {dgId: $dgId, project: $project})-[:HAS_REPRESENTATION]->(r:Representation {nativeId: $nativeId, platform: $platform, project: $project})
        RETURN count(r) AS cnt
        // op=DETACH_COUNT
        """,
        {"dgId": dg_id, "platform": platform, "nativeId": native_id, "project": project},
    ).single()
    if count_row is None or count_row["cnt"] == 0:
        raise DgIdentityError(
            f"No representation bound to dgId '{dg_id}' for native id '{native_id}'.",
            code="DGID_NOT_FOUND",
        )

    session.run(
        """
        MATCH (e {dgId: $dgId, project: $project})-[:HAS_REPRESENTATION]->(r:Representation {nativeId: $nativeId, platform: $platform, project: $project})
        DETACH DELETE r
        // op=DETACH
        """,
        {"dgId": dg_id, "platform": platform, "nativeId": native_id, "project": project},
    )
    return True
