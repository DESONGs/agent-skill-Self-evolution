from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..bootstrap import ensure_source_layout
from ..runtime import run_runtime
from .models import (
    ExecuteSkillRequest,
    ExecuteSkillResponse,
    FindSkillRequest,
    FindSkillResponse,
    RuntimeExecutionResponse,
    SkillProjection,
)
from .search import EngineSearchService

ensure_source_layout()


RuntimeRunner = Callable[..., dict[str, Any]]


def _coerce_projection(value: SkillProjection | dict[str, Any]) -> SkillProjection:
    if isinstance(value, SkillProjection):
        return value
    return SkillProjection.from_dict(value)


def _coerce_request(request: ExecuteSkillRequest | dict[str, Any] | str, **kwargs: Any) -> ExecuteSkillRequest:
    if isinstance(request, ExecuteSkillRequest):
        if kwargs:
            payload = request.to_dict()
            payload.update(kwargs)
            return ExecuteSkillRequest.from_dict(payload)
        return request
    if isinstance(request, str):
        payload = {"skill_id": request, **kwargs}
        return ExecuteSkillRequest.from_dict(payload)
    payload = dict(request)
    payload.update(kwargs)
    return ExecuteSkillRequest.from_dict(payload)


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
        return isinstance(value, Mapping)
    return True


def _validate_parameters(parameters: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    if not schema:
        return
    if schema.get("type") not in {None, "object"}:
        return

    required = [str(item) for item in schema.get("required", []) if str(item).strip()]
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError(f"Missing required parameter(s): {', '.join(sorted(missing))}")

    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return
    for name, definition in properties.items():
        if name not in parameters or not isinstance(definition, Mapping):
            continue
        expected_type = definition.get("type")
        if not _schema_type_matches(str(expected_type) if expected_type is not None else None, parameters[name]):
            raise ValueError(f"Parameter {name!r} must be of type {expected_type!r}")


class EngineService:
    def __init__(
        self,
        registry_service: Any,
        *,
        runtime_runner: RuntimeRunner | None = None,
        search_service: EngineSearchService | None = None,
    ):
        self.registry_service = registry_service
        self.runtime_runner = runtime_runner or run_runtime
        self.search_service = search_service or EngineSearchService(self.registry_service)

    def find_skill(self, request: FindSkillRequest | dict[str, Any] | str, **kwargs: Any) -> FindSkillResponse:
        return self.search_service.search(request, **kwargs)

    def execute_skill(
        self,
        request: ExecuteSkillRequest | dict[str, Any] | str,
        **kwargs: Any,
    ) -> ExecuteSkillResponse:
        normalized_request = _coerce_request(request, **kwargs)
        if not normalized_request.skill_id:
            raise ValueError("skill_id is required")

        projection_payload = self.registry_service.get_skill_projection(
            normalized_request.skill_id,
            version_id=normalized_request.version_id,
        )
        projection = _coerce_projection(projection_payload)
        _validate_parameters(normalized_request.parameters, projection.parameter_schema)

        install_bundle = self.registry_service.resolve_install_bundle(
            normalized_request.skill_id,
            version_id=normalized_request.version_id,
        )
        action_id = normalized_request.action_id or projection.default_action_id or install_bundle.get("default_action")
        if not action_id:
            raise ValueError(f"No executable action available for skill {normalized_request.skill_id!r}")
        package_root = install_bundle.get("package_root") or install_bundle.get("bundle_root") or install_bundle.get("bundle_path")
        if not package_root:
            raise KeyError(f"Install bundle for skill {normalized_request.skill_id!r} does not expose a package root")

        runtime_payload = self.runtime_runner(
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


def open_engine(
    root: str | Path | None = None,
    *,
    mode: str | None = None,
    base_url: str | None = None,
) -> EngineService:
    from ..registry.adapter import RegistryAdapter

    return EngineService(RegistryAdapter(root, mode=mode, base_url=base_url))


def find_skill(
    root: str | Path | None,
    request: FindSkillRequest | dict[str, Any] | str,
    *,
    mode: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return open_engine(root, mode=mode, base_url=base_url).find_skill(request, **kwargs).to_dict()


def execute_skill(
    root: str | Path | None,
    request: ExecuteSkillRequest | dict[str, Any] | str,
    *,
    mode: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return open_engine(root, mode=mode, base_url=base_url).execute_skill(request, **kwargs).to_dict()
