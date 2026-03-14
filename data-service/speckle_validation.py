from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

from specklepy.api import operations
from specklepy.api.client import SpeckleClient
from specklepy.core.api.inputs.model_inputs import CreateModelInput
from specklepy.core.api.inputs.version_inputs import CreateVersionInput
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

    models = client.model.get_models(project_id)
    for model in models.items:
        if getattr(model, "name", None) == name:
            return model.id

    created = client.model.create(
        CreateModelInput(
            name=name,
            description="DG validation overlay generated from Grasshopper validation runs.",
            projectId=project_id,
        )
    )
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
