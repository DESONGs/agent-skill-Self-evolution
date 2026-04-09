from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import PromotionSubmission
from ..services.container import get_service_container
from ..services.registry_service import EnterpriseRegistryService


def open_registry(root: str | Path | None = None) -> EnterpriseRegistryService:
    return get_service_container().registry_service


def publish_package(root: str | Path | None, source: str | Path) -> dict[str, Any]:
    return open_registry(root).publish_package(source)


def resolve_install_bundle(root: str | Path | None, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
    return open_registry(root).resolve_install_bundle(skill_id, version_id=version_id)


def ingest_feedback(root: str | Path | None, envelope: Any) -> dict[str, Any]:
    return get_service_container().feedback_service.ingest(envelope)


def submit_promotion(root: str | Path | None, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
    return get_service_container().promotion_service.submit(submission)


def build_registry_app(root: str | Path | None = None) -> Any:
    from .api import create_registry_app

    return create_registry_app(root)


def build_engine_app(root: str | Path | None = None) -> Any:
    from .api import create_engine_app

    return create_engine_app(root)


def list_skills(root: str | Path | None = None) -> list[dict[str, Any]]:
    return open_registry(root).list_skills()


def get_skill(root: str | Path | None, skill_id: str) -> dict[str, Any]:
    return open_registry(root).get_skill(skill_id)


def get_skill_projection(root: str | Path | None, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
    return open_registry(root).get_skill_projection(skill_id, version_id=version_id)


def list_skill_projections(root: str | Path | None = None) -> list[dict[str, Any]]:
    return open_registry(root).list_skill_projections()


def find_skill_projection(root: str | Path | None, request: Any, **kwargs: Any) -> dict[str, Any]:
    return get_service_container().projection_service.find_skill(request, **kwargs).to_dict()


def execute_skill_projection(root: str | Path | None, request: Any, **kwargs: Any) -> dict[str, Any]:
    if kwargs:
        if isinstance(request, dict):
            payload = dict(request)
            payload.update(kwargs)
            request = payload
        elif isinstance(request, str):
            request = {"skill_id": request, **kwargs}
    return get_service_container().execution_service.execute(request).to_dict()


def open_engine(root: str | Path | None = None) -> Any:
    return get_service_container().execution_service


__all__ = [
    "EnterpriseRegistryService",
    "build_engine_app",
    "build_registry_app",
    "execute_skill_projection",
    "find_skill_projection",
    "get_skill",
    "get_skill_projection",
    "ingest_feedback",
    "list_skill_projections",
    "list_skills",
    "open_engine",
    "open_registry",
    "publish_package",
    "resolve_install_bundle",
    "submit_promotion",
]
