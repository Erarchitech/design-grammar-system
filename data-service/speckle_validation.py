from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

from specklepy.api import operations
from specklepy.api.client import SpeckleClient
from specklepy.core.api.inputs.model_inputs import CreateModelInput
from specklepy.core.api.inputs.version_inputs import CreateVersionInput, DeleteVersionsInput
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline
from specklepy.transports.server import ServerTransport


class SpeckleValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeckleConnectionSettings:
    base_url: str
    internal_url: str
    write_token: str
    read_token: str
    dg_base_url: str


def normalize_url(url: str) -> str:
    return url.rstrip("/")


def build_client(base_url: str, token: str) -> SpeckleClient:
    normalized = normalize_url(base_url)
    parsed = urlparse(normalized)
    host = parsed.netloc or parsed.path
    use_ssl = parsed.scheme != "http"
    client = SpeckleClient(host=host, use_ssl=use_ssl)
    client.authenticate_with_token(token)
    return client


def get_or_create_validation_model_id(
    client: SpeckleClient,
    project_id: str,
    configured_model_id: str | None,
    name: str = "dg-validation",
) -> str:
    if configured_model_id:
        return configured_model_id

    def existing() -> str | None:
        for model in client.model.get_models(project_id).items:
            if getattr(model, "name", None) == name:
                return model.id
        return None

    found = existing()
    if found:
        return found
    try:
        created = client.model.create(
            CreateModelInput(
                name=name,
                description="DG validation overlay generated from Grasshopper validation runs.",
                projectId=project_id,
            )
        )
    except Exception:
        # A Revit check publishes its rules in parallel: on a fresh Speckle project another publish may have created
        # the model between the listing and this create (live 2026-10-29, "A branch with this name already exists").
        found = existing()
        if found:
            return found
        raise
    return created.id


def get_latest_model_version_id(client: SpeckleClient, project_id: str, model_id: str) -> str:
    versions = client.version.get_versions(model_id, project_id, limit=1)
    if not versions.items:
        raise SpeckleValidationError(
            f"Base model '{model_id}' in Speckle project '{project_id}' has no versions to overlay."
        )

    return versions.items[0].id


def build_model_version_url(base_url: str, project_id: str, model_id: str, version_id: str) -> str:
    normalized = normalize_url(base_url)
    return f"{normalized}/projects/{quote(project_id)}/models/{quote(model_id)}@{quote(version_id)}"


def build_model_viewer_url(dg_base_url: str, project: str, run_id: str) -> str:
    normalized = normalize_url(dg_base_url)
    return f"{normalized}/model-viewer/?project={quote(project)}&runId={quote(run_id)}"


def publish_validation_version(
    settings: SpeckleConnectionSettings,
    *,
    dg_project: str,
    speckle_project_id: str,
    base_model_id: str,
    base_version_id: str,
    validation_model_id: str,
    run_id: str,
    rules: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> dict[str, str]:
    client = build_client(settings.internal_url, settings.write_token)
    transport = ServerTransport(speckle_project_id, client=client)
    root = Base()
    root["name"] = f"DG Validation {run_id}"
    root["dgProject"] = dg_project
    root["validationRunId"] = run_id
    root["baseModelId"] = base_model_id
    root["baseVersionId"] = base_version_id
    root["rules"] = rules
    root["elements"] = [build_validation_entity(entity) for entity in entities]

    object_id = operations.send(root, [transport])
    version = client.version.create(
        CreateVersionInput(
            objectId=object_id,
            modelId=validation_model_id,
            projectId=speckle_project_id,
            message=f"DG validation run {run_id}",
            sourceApplication="design-grammars",
            totalChildrenCount=len(entities),
        )
    )

    return {
        "validationModelId": validation_model_id,
        "validationVersionId": version.id,
        "baseVersionId": base_version_id,
        "modelViewerUrl": build_model_viewer_url(settings.dg_base_url, dg_project, run_id),
        "validationResourceUrl": build_model_version_url(
            settings.base_url,
            speckle_project_id,
            validation_model_id,
            version.id,
        ),
        "baseResourceUrl": build_model_version_url(
            settings.base_url,
            speckle_project_id,
            base_model_id,
            base_version_id,
        ),
    }


def context_nodes(elements: list[dict[str, Any]]) -> list[Base]:
    """Neutral context objects (walls, columns, beams, doors, windows): no dgEntityId, so the viewer never colours
    them as passed or failed."""
    nodes = []
    for element in elements:
        node = Base()
        node["name"] = element.get("label") or "context"
        node["dgContext"] = True
        node["displayValue"] = build_display_value(element.get("geometry"))
        if node["displayValue"]:
            nodes.append(node)
    return nodes


def add_context_to_validation_version(
    settings: SpeckleConnectionSettings,
    *,
    speckle_project_id: str,
    validation_model_id: str,
    validation_version_id: str,
    nodes: list[Base],
    run_id: str,
) -> str:
    """Phase 1303-15: the Model Viewer loads only a run's validation version (never the base model), so the model
    context of a check is appended to it: the run's version is read, the context nodes are appended to
    ``elements`` (replacing context from an earlier pass), and a new version of the validation model is created. Returns its id."""
    client = build_client(settings.internal_url, settings.write_token)
    transport = ServerTransport(speckle_project_id, client=client)
    version = client.version.get(validation_version_id, speckle_project_id)
    root = operations.receive(version.referenced_object, transport)
    existing = [e for e in (getattr(root, "elements", None) or []) if not getattr(e, "dgContext", False)]
    root["elements"] = existing + list(nodes)  # rendered like the entities; no dgEntityId, so never coloured
    object_id = operations.send(root, [transport])
    created = client.version.create(
        CreateVersionInput(
            objectId=object_id,
            modelId=validation_model_id,
            projectId=speckle_project_id,
            message=f"DG validation run {run_id} with model context",
            sourceApplication="design-grammars",
            totalChildrenCount=len(root["elements"]),
        )
    )
    return created.id


def snapshot_node(element: dict[str, Any]) -> Base:
    """One element of a model snapshot (Phase 1303-26): its UniqueId, classes and mapping state ride on the node, so
    the Model Viewer colours it by class or by state without another request."""
    node = Base()
    node["name"] = element.get("name") or element.get("dgNativeId") or "element"
    for key in ("dgSnapshotId", "dgProject", "dgNativeId", "dgRevitId", "dgMappingState"):
        node[key] = element.get(key)
    node["dgClassIris"] = list(element.get("dgClassIris") or [])
    node["dgClassLabels"] = list(element.get("dgClassLabels") or [])
    node["displayValue"] = build_display_value(element.get("geometry"))
    return node


def publish_snapshot_version(
    settings: SpeckleConnectionSettings,
    *,
    dg_project: str,
    speckle_project_id: str,
    model_id: str,
    snapshot_id: str,
    document: str,
    elements: list[dict[str, Any]],
) -> str:
    """Phase 1303-26 (D-79): the mapping view of a confirmed mapping as one version of the snapshot model. Returns
    the version id."""
    client = build_client(settings.internal_url, settings.write_token)
    transport = ServerTransport(speckle_project_id, client=client)
    root = Base()
    root["name"] = f"DG model snapshot {snapshot_id}"
    root["dgProject"] = dg_project
    root["dgSnapshotId"] = snapshot_id
    root["document"] = document
    root["elements"] = [snapshot_node(e) for e in elements]
    object_id = operations.send(root, [transport])
    version = client.version.create(
        CreateVersionInput(
            objectId=object_id,
            modelId=model_id,
            projectId=speckle_project_id,
            message=f"DG model snapshot {snapshot_id} ({document})",
            sourceApplication="design-grammars",
            totalChildrenCount=len(elements),
        )
    )
    return version.id


def delete_validation_version(
    settings: SpeckleConnectionSettings,
    *,
    speckle_project_id: str,
    validation_version_id: str,
) -> bool:
    client = build_client(settings.internal_url, settings.write_token)
    deleted = client.version.delete(
        DeleteVersionsInput(
            versionIds=[validation_version_id],
            projectId=speckle_project_id,
        )
    )
    if not deleted:
        raise SpeckleValidationError(
            f"Speckle did not confirm deletion of validation version '{validation_version_id}' in project '{speckle_project_id}'."
        )
    return True


def build_validation_entity(entity: dict[str, Any]) -> Base:
    node = Base()
    dg_entity_id = entity.get("dgEntityId") or ""
    node["name"] = entity.get("displayName") or dg_entity_id
    node["dgEntityId"] = dg_entity_id
    node["displayName"] = entity.get("displayName")
    node["dgProject"] = entity.get("dgProject")
    node["validationRunId"] = entity.get("validationRunId")
    node["ruleIds"] = entity.get("ruleIds") or []
    node["failedRuleIds"] = entity.get("failedRuleIds") or []
    node["passedRuleIds"] = entity.get("passedRuleIds") or []
    node["overallStatus"] = entity.get("overallStatus") or "unknown"
    node["baseModelId"] = entity.get("baseModelId")
    node["baseVersionId"] = entity.get("baseVersionId")
    node["displayValue"] = build_display_value(entity.get("geometry"))
    return node


def build_display_value(geometry: dict[str, Any] | None) -> list[Any]:
    if not geometry:
        return []

    units = geometry.get("units") or "m"
    items = geometry.get("items") or []
    display_items: list[Any] = []
    for item in items:
        kind = (item.get("kind") or "").lower()
        if kind == "mesh":
            vertices = [float(value) for value in item.get("vertices") or []]
            faces = encode_mesh_faces(item.get("faces") or [])
            colors = [int(value) for value in item.get("colors") or []]
            if vertices and faces:
                display_items.append(
                    Mesh(
                        vertices=vertices,
                        faces=faces,
                        colors=colors,
                        units=units,
                        applicationId=item.get("applicationId"),
                    )
                )
        elif kind == "point":
            values = [float(value) for value in item.get("values") or []]
            if len(values) >= 3:
                display_items.append(Point(x=values[0], y=values[1], z=values[2], units=units))
        elif kind == "line":
            values = [float(value) for value in item.get("values") or []]
            if len(values) >= 6:
                display_items.append(
                    Line(
                        start=Point(x=values[0], y=values[1], z=values[2], units=units),
                        end=Point(x=values[3], y=values[4], z=values[5], units=units),
                        units=units,
                    )
                )
        elif kind == "polyline":
            values = [float(value) for value in item.get("values") or []]
            if len(values) >= 6:
                display_items.append(Polyline(value=values, units=units))

    return display_items


def encode_mesh_faces(faces: list[list[int]]) -> list[int]:
    encoded: list[int] = []
    for face in faces:
        if len(face) < 3:
            continue
        encoded.append(len(face))
        encoded.extend(int(index) for index in face)
    return encoded
