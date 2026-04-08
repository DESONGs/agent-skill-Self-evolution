from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from ..engine.models import ExecuteSkillRequest, ExecuteSkillResponse, RuntimeExecutionResponse, SkillProjection
from ..runtime import run_runtime
from ..storage.object_store.client import ObjectStoreClient
from ..storage.repositories.registry_repository import RegistryRepository


def _schema_type_matches(expected: str | None, value: Any) -> bool:
    if not expected or expected == "any":
        return True
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def _validate_parameters(parameters: dict[str, Any], schema: dict[str, Any]) -> None:
    if not schema or schema.get("type") not in {None, "object"}:
        return
    required = [str(item) for item in schema.get("required", []) if str(item).strip()]
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError(f"Missing required parameter(s): {', '.join(sorted(missing))}")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return
    for name, definition in properties.items():
        if name not in parameters or not isinstance(definition, dict):
            continue
        expected_type = definition.get("type")
        if not _schema_type_matches(str(expected_type) if expected_type is not None else None, parameters[name]):
            raise ValueError(f"Parameter {name!r} must be of type {expected_type!r}")


class ExecutionService:
    def __init__(self, repository: RegistryRepository, object_store: ObjectStoreClient):
        self.repository = repository
        self.object_store = object_store

    def execute(self, request: ExecuteSkillRequest | dict[str, Any] | str) -> ExecuteSkillResponse:
        normalized_request = request if isinstance(request, ExecuteSkillRequest) else ExecuteSkillRequest.from_dict(
            {"skill_id": request} if isinstance(request, str) else request
        )
        if not normalized_request.skill_id:
            raise ValueError("skill_id is required")

        projection = SkillProjection.from_dict(
            self.repository.get_skill_projection(normalized_request.skill_id, version_id=normalized_request.version_id)
        )
        _validate_parameters(normalized_request.parameters, projection.parameter_schema)
        version_payload = self.repository.get_version_payload(normalized_request.skill_id, version_id=normalized_request.version_id)
        temp_root = Path(tempfile.mkdtemp(prefix="asp-enterprise-exec-"))
        try:
            bundle_path = self.object_store.download_file(version_payload["package_object_key"], temp_root / "package.zip")
            extract_root = temp_root / "package"
            with zipfile.ZipFile(bundle_path) as archive:
                archive.extractall(extract_root)
            roots = [path for path in extract_root.iterdir() if path.is_dir()]
            if len(roots) != 1:
                raise ValueError("Package bundle must contain exactly one root directory")
            package_root = roots[0]
            action_id = normalized_request.action_id or projection.default_action_id
            if not action_id:
                raise ValueError(f"No executable action available for skill {normalized_request.skill_id!r}")
            runtime_payload = run_runtime(
                package_root,
                action_id=action_id,
                action_input=normalized_request.parameters,
                workspace_dir=normalized_request.workspace_dir,
                run_id=normalized_request.run_id,
                install_root=normalized_request.install_root,
                env=normalized_request.env,
                max_sandbox=normalized_request.max_sandbox,
                allow_network=normalized_request.allow_network,
            )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

        execution = RuntimeExecutionResponse.from_runtime_payload(
            runtime_payload,
            metadata={
                "trace_id": normalized_request.trace_id,
                "environment_profile": normalized_request.environment_profile,
                "skill_type": projection.skill_type,
            },
        )
        return ExecuteSkillResponse(
            request=normalized_request,
            skill_projection=projection,
            execution=execution,
        )
