"""Model snapshots of a confirmed mapping (Phase 1303-26, owner decisions D-79..D-83, 2026-10-30).

When a confirmed mapping batch has been written into Revit, DG asks the DG Revit connector that wrote it for one mesh per
element of the mapping session and for the model fingerprint (composition and positions of the mapped categories). It
publishes those meshes as one Speckle version on the model ``dg-model-snapshots`` and records a standalone
``(:DesignState {kind:'ObjState', source:'mapping-snapshot'})``: the model snapshot («Снимок модели»). A later Revit
check whose fingerprint equals the latest snapshot's attaches its runs to it (``run.modelSnapshotId`` and
``(run)-[:IN_SNAPSHOT]->(snapshot)``); the run's own statePayloadJson and computed StateId are never changed.

``take`` is the orchestration; every outside call (Neo4j, the connector job queue, Speckle) is passed in, so the tests
run it with fakes. Nothing here raises into the mapping apply route: a failure is recorded on the batch.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

GRAPH = "ValidGraph"
SOURCE = "mapping-snapshot"
KIND = "ObjState"
SPECKLE_MODEL = "dg-model-snapshots"
JOB_KIND = "snapshot"
JOB_WAIT_S = 180.0
CONTEXT_WAIT_S = 300.0
PENDING, PUBLISHED, FAILED = "pending", "published", "failed"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_id(project: str, session_id: str, batch_id: str) -> str:
    """One snapshot per confirmed batch: deterministic, so a second acknowledgement finds the same node."""
    digest = hashlib.sha256(f"{project}|{session_id}|{batch_id}".encode("utf-8")).hexdigest()
    return "OS_" + digest[:16]


def categories(descriptors: list[dict]) -> list[str]:
    """The Revit categories the mapping read (descriptor ``category`` = Category.Name)."""
    return sorted({str(d.get("category") or "").strip() for d in descriptors or [] if str(d.get("category") or "").strip()})


def _local(iri: str) -> str:
    text = str(iri or "")
    return text.replace("#", "/").replace(":", "/").rstrip("/").rsplit("/", 1)[-1] or text


def elements(result: dict, descriptors: list[dict]) -> list[dict]:
    """The session's elements as the view shows them: UniqueId, label, Revit id, classes and mapping state."""
    by_id = {str(d.get("nativeId")): d for d in descriptors or [] if d.get("nativeId")}
    out = []
    for element in (result or {}).get("elements") or []:
        native_id = str(element.get("nativeId") or "")
        if not native_id:
            continue
        descriptor = by_id.get(native_id, {})
        iris, labels = [], []
        for role in element.get("roles") or []:
            iri = role.get("classIri")
            if iri and iri not in iris:
                iris.append(iri)
                labels.append(role.get("label") or _local(iri))
        revit_id = descriptor.get("elementId")
        name = str(descriptor.get("name") or "").strip()
        out.append({
            "nativeId": native_id,
            "label": (f"{name} [{revit_id}]" if name and revit_id is not None else name or native_id),
            "revitId": revit_id,
            "category": descriptor.get("category") or "",
            "classIris": iris,
            "classLabels": labels,
            "state": element.get("state") or "unmapped",
        })
    return out


def bbox_mm(mesh: Optional[dict]) -> Optional[list[int]]:
    """[minX, minY, minZ, maxX, maxY, maxZ] of a mesh in mm, rounded to 1 mm; None without vertices."""
    xs, ys, zs = [], [], []
    for item in (mesh or {}).get("items") or []:
        v = item.get("vertices") or []
        xs.extend(v[0::3])
        ys.extend(v[1::3])
        zs.extend(v[2::3])
    if not xs:
        return None
    return [round(min(xs)), round(min(ys)), round(min(zs)), round(max(xs)), round(max(ys)), round(max(zs))]


def payload(snapshot_state_id: str, document: str, captured_at: str, items: list[dict], meshes: dict) -> str:
    """statePayloadJson of the snapshot: the v2 envelope, objStates only (one per element)."""
    obj_states = [{
        "stateId": "OS_" + hashlib.sha256(f"{snapshot_state_id}|{e['nativeId']}".encode("utf-8")).hexdigest()[:16],
        "ref": e["nativeId"],
        "label": e["label"],
        "classIris": e["classIris"],
        "mappingState": e["state"],
        "bboxMm": bbox_mm(meshes.get(e["nativeId"])),
    } for e in items]
    return json.dumps({"version": "2", "stateId": snapshot_state_id, "label": f"Mapping · {document}",
                       "capturedAtUtc": captured_at, "objStates": obj_states, "paramStates": [], "propStates": []},
                      ensure_ascii=False, sort_keys=True)


def speckle_elements(items: list[dict], meshes: dict, snapshot_state_id: str, project: str) -> list[dict]:
    """One node per element that has a mesh; speckle_validation.snapshot_node turns it into a Speckle object."""
    out = []
    for e in items:
        mesh = meshes.get(e["nativeId"])
        if not mesh:
            continue
        out.append({"name": e["label"], "dgSnapshotId": snapshot_state_id, "dgProject": project,
                    "dgNativeId": e["nativeId"], "dgRevitId": e["revitId"], "dgClassIris": e["classIris"],
                    "dgClassLabels": e["classLabels"], "dgMappingState": e["state"], "geometry": mesh})
    return out


def summary(node: dict) -> dict:
    """The snapshot as a Design State group of the Model Viewer (same keys as a run's state summary)."""
    return {
        "stateId": node.get("StateId"),
        "kind": "snapshot",
        "label": node.get("label"),
        "capturedAtUtc": node.get("capturedAtUtc"),
        "parameterCount": node.get("elementCount"),
        "elementCount": node.get("elementCount"),
        "mappingSessionId": node.get("mappingSessionId"),
        "batchId": node.get("batchId"),
        "document": node.get("document"),
    }


# --- Neo4j -----------------------------------------------------------------------------------------------------------

SAVE_QUERY = """
// op=model_snapshot_save
MERGE (ds:DesignState {graph:$graph, project:$project, StateId:$stateId})
ON CREATE SET ds += $props
RETURN ds.StateId AS stateId
"""

LATEST_QUERY = """
// op=model_snapshot_latest
MATCH (ds:DesignState {graph:$graph, project:$project, source:$source})
RETURN ds {.*} AS ds
ORDER BY ds.capturedAtUtc DESC, ds.StateId DESC
LIMIT 1
"""

LIST_QUERY = """
// op=model_snapshot_list
MATCH (ds:DesignState {graph:$graph, project:$project, source:$source})
RETURN ds {.StateId, .label, .capturedAtUtc, .elementCount, .mappingSessionId, .batchId, .document} AS ds
ORDER BY ds.capturedAtUtc DESC, ds.StateId DESC
LIMIT $limit
"""

GET_QUERY = """
// op=model_snapshot_get
MATCH (ds:DesignState {graph:$graph, project:$project, source:$source, StateId:$stateId})
RETURN ds {.*} AS ds
"""

ATTACH_QUERY = """
// op=model_snapshot_attach_runs
MATCH (ds:DesignState {graph:$graph, project:$project, source:$source, StateId:$stateId})
MATCH (run:ValidationRun {graph:$graph, project:$project})
WHERE run.runId IN $runIds
SET run.modelSnapshotId = ds.StateId
MERGE (run)-[:IN_SNAPSHOT]->(ds)
RETURN count(run) AS attached
"""


def _rows(session, query: str, params: dict) -> list:
    return [dict(r) for r in session.run(query, params)]


def save(session, project: str, props: dict) -> str:
    rows = _rows(session, SAVE_QUERY, {"graph": GRAPH, "project": project, "stateId": props["StateId"],
                                       "props": {**props, "graph": GRAPH, "project": project, "kind": KIND,
                                                 "source": SOURCE}})
    return rows[0]["stateId"] if rows else props["StateId"]


def latest(session, project: str) -> Optional[dict]:
    rows = _rows(session, LATEST_QUERY, {"graph": GRAPH, "project": project, "source": SOURCE})
    return rows[0]["ds"] if rows else None


def get(session, project: str, snapshot_state_id: str) -> Optional[dict]:
    rows = _rows(session, GET_QUERY, {"graph": GRAPH, "project": project, "source": SOURCE,
                                      "stateId": snapshot_state_id})
    return rows[0]["ds"] if rows else None


def list_snapshots(session, project: str, limit: int = 50) -> list[dict]:
    rows = _rows(session, LIST_QUERY, {"graph": GRAPH, "project": project, "source": SOURCE, "limit": int(limit)})
    return [summary(r["ds"]) for r in rows]


def attach_runs(session, project: str, snapshot_state_id: str, run_ids: list[str]) -> int:
    if not run_ids:
        return 0
    rows = _rows(session, ATTACH_QUERY, {"graph": GRAPH, "project": project, "source": SOURCE,
                                         "stateId": snapshot_state_id, "runIds": list(run_ids)})
    return int(rows[0]["attached"]) if rows else 0


def attach_decision(snapshot: Optional[dict], result: dict) -> dict:
    """D-81: a check joins the latest snapshot only when it reported the same fingerprint."""
    if not snapshot:
        return {"attached": False, "reason": "no model snapshot in the project"}
    fingerprint = (result or {}).get("fingerprint")
    if not fingerprint:
        return {"attached": False, "stateId": snapshot.get("StateId"),
                "reason": "the check did not report a model fingerprint"}
    if fingerprint != snapshot.get("fingerprint"):
        return {"attached": False, "stateId": snapshot.get("StateId"),
                "reason": "the model changed since the mapping was confirmed"}
    return {"attached": True, "stateId": snapshot.get("StateId")}


# --- orchestration ---------------------------------------------------------------------------------------------------

def take(project: str, session_id: str, batch_id: str, *, load_session: Callable[[], Optional[dict]],
         mark: Callable[[dict], None], submit: Callable[[dict], dict], wait: Callable[[dict, float, str], bool],
         program: Callable[[], dict], publish: Callable[[str, str, list], dict], store: Callable[[dict], str],
         now: Callable[[], str] = utc_now) -> dict:
    """Snapshot one written batch -> the batch's snapshot status ({status, stateId?, reason?}); never raises.

    ``mark(status)`` records the status on the batch; ``submit(payload)`` queues the connector job; ``wait(job, s,
    until)`` waits for its result or context; ``publish(stateId, document, nodes)`` creates the Speckle version and
    answers its ids; ``store(props)`` writes the DesignState node."""
    snapshot_id = state_id(project, session_id, batch_id)
    status: dict[str, Any] = {"status": PENDING, "stateId": snapshot_id}
    try:
        meta = load_session()
        if not meta:
            return _fail(mark, status, "the mapping session is gone")
        if (meta.get("platform") or "") != "revit":
            return {"status": "skipped", "reason": "only Revit mappings are snapshotted"}
        batch = next((b for b in meta.get("batches") or [] if b.get("batchId") == batch_id), None)
        if batch is None or (batch.get("delivery") or {}).get("state") != "written":
            return {"status": "skipped", "reason": "the batch was not written into Revit"}
        if (batch.get("snapshot") or {}).get("status") in (PENDING, PUBLISHED):
            return dict(batch["snapshot"])
        items = elements(meta.get("result") or {}, meta.get("descriptors") or [])
        cats = categories(meta.get("descriptors") or [])
        if not items:
            return _fail(mark, status, "the mapping session has no elements")
        mark(dict(status))
        script = program()
        job = submit({"script": script["source"], "sha256": script["sha256"],
                      "uniqueIds": [e["nativeId"] for e in items], "categories": cats})
        if not wait(job, JOB_WAIT_S, "finished") or job.get("status") != "done":
            return _fail(mark, status, "Revit did not answer the snapshot: %s" % (job.get("error") or "no answer in time"))
        if not wait(job, CONTEXT_WAIT_S, "context"):
            return _fail(mark, status, "the element meshes did not arrive in time")
        answer = job.get("result") or {}
        meshes = {str(e.get("uniqueId")): e.get("mesh") for e in job.get("context") or [] if e.get("mesh")}
        document = str(answer.get("document") or meta.get("label") or "")
        nodes = speckle_elements(items, meshes, snapshot_id, project)
        if not nodes:
            return _fail(mark, status, "Revit answered no element geometry")
        speckle = publish(snapshot_id, document, nodes)
        captured = now()
        store({
            "StateId": snapshot_id, "mappingSessionId": session_id, "batchId": batch_id, "document": document,
            "label": f"Mapping · {document}" if document else "Mapping", "fingerprint": answer.get("fingerprint"),
            "fingerprintCount": answer.get("count"), "categories": cats, "elementCount": len(items),
            "meshCount": len(nodes), "capturedAtUtc": captured,
            "speckleProjectId": speckle.get("speckleProjectId"), "speckleModelId": speckle.get("speckleModelId"),
            "speckleVersionId": speckle.get("speckleVersionId"),
            "statePayloadJson": payload(snapshot_id, document, captured, items, meshes),
        })
        status = {"status": PUBLISHED, "stateId": snapshot_id, "elements": len(items), "meshes": len(nodes),
                  "missing": len(answer.get("missing") or [])}
        mark(dict(status))
        return status
    except Exception as exc:  # noqa: BLE001 - recorded on the batch, never raised into the apply route
        return _fail(mark, status, str(exc)[:300] or exc.__class__.__name__)


def _fail(mark, status: dict, reason: str) -> dict:
    failed = {"status": FAILED, "stateId": status.get("stateId"), "reason": reason}
    try:
        mark(dict(failed))
    except Exception:  # noqa: BLE001
        pass
    return failed
