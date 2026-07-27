"""Parser-faithful Frame envelope fixture builders (Phase 37 Wave 0: SVAL-01/02/03).

These are pure-data builders -- no pytest import, no Neo4j, no `app` import --
that every later Phase 37 plan publishes via `computgraph_publish.publish_structure()`
or `POST /computgraph/publish`. They derive from `test_computgraph_publish.py`'s
`_frame_cg_context()` (same cgContextJson v1 envelope shape: `schemaVersion`,
`project`, `definition`, `object`, `algorithms`, `untagged`, `nodes`, `wires`,
`warnings`) but scoped to `FIXTURE_PROJECT`, which is deliberately distinct from
that suite's `GOLDEN_PROJECT` ("p1") so both suites can publish into one live
Neo4j without contaminating each other's node counts (T-37-05).

Procedure naming and cgId minting are parser-faithful:
- `CanvasAnnotationParser.ProcedureId(alg, nn)` mints the bare index
  (`cg:{alg}:proc:{nn}`), NOT the `{nn}_Proc` token the older Phase 36 fixture
  uses -- do not change that older fixture; its `GOLDEN_CG_ID` anchors the
  pinned dgId golden vector `dg:BC8E62EE137E2B56`.
- `ProcedureRegex` (`^(?<nn>\\d+)_Proc - (?<name>.+)$`) captures the text AFTER
  the separator, so the real Frame canvas group `12_Proc - 2D Footer
  Configuration` parses to the bare name `2D Footer Configuration`
  (`DG/tests/DG.Tests/Fixtures/frame-cg-context.json` L16). This fidelity is
  load-bearing: the SVAL-02 `requiresProcedure` rule matches a `Footer`
  substring against `Procedure.procedureName`, and against the older
  fixture's literal `"12_Proc"` name that rule could never fire.

The `11_Var_HTotal` convention token (`DG/tests/DG.Tests/Fixtures/frame-cg-context.json`
L32) lives only in `PARAM_HTOTAL_CG_ID`'s last segment -- the bare display
`name` is just `HTotal`. That cgId-embedded token is the string SC3 requires a
consult answer to cite.
"""

from __future__ import annotations

import copy
from typing import Any

FIXTURE_PROJECT = "p37-structure"

FRAME_DEFINITION_ID = "frame.gh"
FRAME_NO_INTERFACE_DEFINITION_ID = "frame-no-interface.gh"
FRAME_NO_FOOTER_DEFINITION_ID = "frame-no-footer.gh"

# ProcedureId(alg, nn) => f"cg:{alg}:proc:{nn}" -- bare index, no "_Proc" token.
PROC_11_CG_ID = "cg:1:proc:11"
PROC_12_CG_ID = "cg:1:proc:12"

# Parser-faithful bare names (ProcedureRegex captures the text after " - ").
PROC_11_NAME = "2D Truss Configuration"
PROC_12_NAME = "2D Footer Configuration"

PARAM_HTOTAL_CG_ID = "cg:1:param:11_Var_HTotal"

# DG.Grasshopper.Components.ParameterStateComponent.ComponentGuid -- same literal
# computgraph_publish.PARAMETER_STATE_COMPONENT_GUID matches against.
PARAMETER_STATE_COMPONENT_GUID = "a2e8c4f1-6b3d-4a9c-8e5f-2d7b0c1a3f6e"

# JOIN A fixture: the PARAMETER STATE input's NickName ("Spans") deliberately
# differs from the Parameter's convention-derived name ("SpansCount") -- that
# divergence is the entire point of JOIN A.
PARAMSTATE_SPANS_NICKNAME = "Spans"


def frame_cg_context(project: str = FIXTURE_PROJECT, definition_id: str = FRAME_DEFINITION_ID) -> dict[str, Any]:
    """A parser-faithful cgContextJson v1 envelope for the Frame fixture: 1
    Object, 1 Algorithm (index 1), 2 Procedures (11 tagged / 12 recognized),
    procedure 11 carries 2 parameters (SpansCount + HTotal). One wire links
    the tagged Parameter's member to the tagged Interface's member (PARAM_LINK
    derivation). `untagged` carries distinct ids that must never reach the
    published store.
    """
    return {
        "schemaVersion": "cg-context-1",
        "project": project,
        "definition": {
            "documentId": definition_id,
            "fileName": "frame.gh",
            "capturedAt": "2026-07-08T00:00:00.0000000Z",
        },
        "object": {
            "name": "FRAME",
            "classIri": None,
            "source": "tagged",
            "dgId": None,
        },
        "algorithms": [
            {
                "index": 1,
                "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": PROC_11_CG_ID,
                        "index": 11,
                        "name": PROC_11_NAME,
                        "source": "tagged",
                        "dgId": None,
                        "memberIds": [],
                        "patterns": [
                            {
                                "id": "cg:1:pat:11_Pat_DivideLine",
                                "label": "Pat",
                                "name": "DivideLine",
                                "hostPatternId": None,
                                "memberIds": ["n-divide-curve"],
                                "source": "tagged",
                                "dgId": None,
                            }
                        ],
                        "parameters": [
                            {
                                "id": "cg:1:param:11_Var_SpansCount",
                                "kind": "Variable",
                                "name": "SpansCount",
                                "dataType": "Integer",
                                "domain": {"min": 1, "max": 20, "step": 1},
                                "memberIds": ["n-spanscount"],
                                "source": "tagged",
                                "dgId": None,
                            },
                            {
                                "id": PARAM_HTOTAL_CG_ID,
                                "kind": "Variable",
                                "name": "HTotal",
                                "dataType": "Float",
                                "domain": {"min": 0.5, "max": 12.0, "step": 0.1},
                                "memberIds": ["n-htotal"],
                                "source": "tagged",
                                "dgId": None,
                            },
                        ],
                        "interfaces": [
                            {
                                "id": "cg:1:intf:11_IntF_ParSplitAt",
                                "name": "ParSplitAt",
                                "ifaceType": "Input",
                                "memberIds": ["n-parsplit"],
                                "source": "tagged",
                                "dgId": None,
                            }
                        ],
                    },
                    {
                        "id": PROC_12_CG_ID,
                        "index": 12,
                        "name": PROC_12_NAME,
                        "source": "recognized",
                        "dgId": None,
                        "memberIds": [],
                        "provider": "anthropic",
                        "model": "claude-sonnet",
                        "confidence": 0.87,
                        "patterns": [
                            {
                                "id": "cg:1:pat:12_Pat_FooterBottom",
                                "label": "Pat",
                                "name": "FooterBottom",
                                "hostPatternId": None,
                                "memberIds": ["n-footer-bottom"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.81,
                                "dgId": None,
                            }
                        ],
                        "parameters": [
                            {
                                "id": "cg:1:param:12_Var_HFooter",
                                "kind": "Variable",
                                "name": "HFooter",
                                "dataType": "Float",
                                "domain": None,
                                "memberIds": ["n-hfooter"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.75,
                                "dgId": None,
                            }
                        ],
                        "interfaces": [
                            {
                                "id": "cg:1:intf:12_IntF_FooterFrame",
                                "name": "FooterFrame",
                                "ifaceType": "Output",
                                "memberIds": ["n-footerframe-intf"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.79,
                                "dgId": None,
                            }
                        ],
                    },
                ],
            }
        ],
        "untagged": {
            "nodeIds": ["n-untagged-01"],
            "groups": [
                {"nickname": "Scratch notes", "memberIds": ["n-scratch-01", "n-scratch-02"]},
            ],
        },
        "nodes": [
            {
                "instanceId": "n-paramstate-1",
                "componentGuid": PARAMETER_STATE_COMPONENT_GUID,
                "name": "PARAMETER STATE",
                "nickname": "PARAMSTATE",
                "position": [0, 0],
                "inputParams": [
                    {
                        "instanceId": "n-paramstate-1-in0",
                        "nickname": PARAMSTATE_SPANS_NICKNAME,
                        "name": "Value",
                        "index": 0,
                    }
                ],
            }
        ],
        "wires": [
            {"fromNode": "n-spanscount", "fromParam": "out0", "toNode": "n-parsplit", "toParam": "in0"},
            {
                "fromNode": "n-spanscount",
                "fromParam": "out0",
                "toNode": "n-paramstate-1",
                "toParam": "n-paramstate-1-in0",
            },
        ],
        "warnings": [],
    }


def frame_without_interface(
    project: str = FIXTURE_PROJECT, definition_id: str = FRAME_NO_INTERFACE_DEFINITION_ID
) -> dict[str, Any]:
    """Deep-copy of the full envelope with procedure 11's `interfaces` emptied
    and any wire targeting the removed interface's member dropped. Everything
    else is identical to `frame_cg_context()`.
    """
    envelope = frame_cg_context(project=project, definition_id=definition_id)
    proc_11 = envelope["algorithms"][0]["procedures"][0]
    removed_member_ids = {
        member_id for iface in proc_11["interfaces"] for member_id in iface.get("memberIds", [])
    }
    proc_11["interfaces"] = []
    envelope["wires"] = [
        wire for wire in envelope["wires"] if wire.get("toNode") not in removed_member_ids
    ]
    return envelope


def frame_without_footer_procedure(
    project: str = FIXTURE_PROJECT, definition_id: str = FRAME_NO_FOOTER_DEFINITION_ID
) -> dict[str, Any]:
    """Deep-copy of the full envelope with the procedure whose id equals
    `PROC_12_CG_ID` removed from the algorithm's procedure list.
    """
    envelope = frame_cg_context(project=project, definition_id=definition_id)
    algorithm = envelope["algorithms"][0]
    algorithm["procedures"] = [
        procedure for procedure in algorithm["procedures"] if procedure["id"] != PROC_12_CG_ID
    ]
    return envelope


def frame_with_normalization_warnings(
    project: str = FIXTURE_PROJECT, definition_id: str = FRAME_DEFINITION_ID
) -> dict[str, Any]:
    """Deep-copy of the full envelope with the top-level `warnings` list set to
    two realistic parser-emitted strings. This is the only path by which
    annotation-convention findings are observable post-publish -- the raw tag
    string itself never reaches Neo4j (`computgraph_publish._build_publish_params`
    strips only `untagged`; `warnings` survives into `Algorithm.contextJson`).
    """
    envelope = frame_cg_context(project=project, definition_id=definition_id)
    envelope["warnings"] = [
        "'11_Emr_UpperChord' normalized to Emergent (Emr→Emg)",
        "Unrecognized nickname 'Scratch notes' left untagged",
    ]
    return envelope


def _deepcopy(envelope: dict[str, Any]) -> dict[str, Any]:
    """Isolation guard reused by callers that need to mutate a builder's
    output without ever touching a previous return value in place."""
    return copy.deepcopy(envelope)
