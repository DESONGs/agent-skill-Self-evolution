from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import PromotionSubmission
from .service import RegistryService


def open_registry(root: str | Path) -> RegistryService:
    return RegistryService(root)


def publish_package(root: str | Path, source: str | Path) -> dict[str, Any]:
    return RegistryService(root).publish_package(source)


def resolve_install_bundle(root: str | Path, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
    return RegistryService(root).resolve_install_bundle(skill_id, version_id=version_id)


def ingest_feedback(root: str | Path, envelope: Any) -> dict[str, Any]:
    return RegistryService(root).ingest_feedback(envelope)


def submit_promotion(root: str | Path, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
    return RegistryService(root).submit_promotion(submission)


def build_registry_app(root: str | Path) -> Any:
    from .api import create_registry_app

    return create_registry_app(root)


def build_engine_app(root: str | Path) -> Any:
    from ..engine import build_engine_app as _build_engine_app

    return _build_engine_app(root)


def list_skills(root: str | Path) -> list[dict[str, Any]]:
    return RegistryService(root).list_skills()


def get_skill(root: str | Path, skill_id: str) -> dict[str, Any]:
    return RegistryService(root).get_skill(skill_id)


def get_skill_projection(root: str | Path, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
    return RegistryService(root).get_skill_projection(skill_id, version_id=version_id)


def list_skill_projections(root: str | Path) -> list[dict[str, Any]]:
    return RegistryService(root).list_skill_projections()


def find_skill_projection(root: str | Path, request: Any, **kwargs: Any) -> dict[str, Any]:
    from ..engine import find_skill as _find_skill

    return _find_skill(root, request, **kwargs)


def execute_skill_projection(root: str | Path, request: Any, **kwargs: Any) -> dict[str, Any]:
    from ..engine import execute_skill as _execute_skill

    return _execute_skill(root, request, **kwargs)


def open_engine(root: str | Path) -> Any:
    from ..engine import open_engine as _open_engine

    return _open_engine(root)


__all__ = [
    "RegistryService",
    "build_registry_app",
    "build_engine_app",
    "execute_skill",
    "execute_skill_projection",
    "get_skill",
    "get_skill_projection",
    "ingest_feedback",
    "find_skill",
    "find_skill_projection",
    "list_skills",
    "list_skill_projections",
    "open_registry",
    "open_engine",
    "publish_package",
    "resolve_install_bundle",
    "submit_promotion",
]
