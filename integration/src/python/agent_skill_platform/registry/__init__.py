from __future__ import annotations

from pathlib import Path
from typing import Any

from ..bootstrap import ensure_source_layout
from ..engine import build_engine_app, execute_skill, find_skill, open_engine
from ..models import PromotionSubmission
from .adapter import RegistryAdapter, RemoteRegistryService
from .service import LocalDevRegistryService

ensure_source_layout()


def open_registry(root: str | Path | None = None, *, mode: str | None = None, base_url: str | None = None) -> RegistryAdapter:
    return RegistryAdapter(root, mode=mode, base_url=base_url)


def publish_package(root: str | Path | None, source: str | Path, *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).publish_package(source)


def resolve_install_bundle(root: str | Path | None, skill_id: str, version_id: str | None = None, *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).resolve_install_bundle(skill_id, version_id=version_id)


def ingest_feedback(root: str | Path | None, envelope: Any, *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).ingest_feedback(envelope)


def submit_promotion(root: str | Path | None, submission: PromotionSubmission | dict[str, Any], *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).submit_promotion(submission)


def build_registry_app(root: str | Path) -> Any:
    from .api import create_registry_app

    return create_registry_app(root)


def list_skills(root: str | Path | None, *, mode: str | None = None, base_url: str | None = None) -> list[dict[str, Any]]:
    return open_registry(root, mode=mode, base_url=base_url).list_skills()


def get_skill(root: str | Path | None, skill_id: str, *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).get_skill(skill_id)


def get_skill_projection(
    root: str | Path | None,
    skill_id: str,
    version_id: str | None = None,
    *,
    mode: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).get_skill_projection(skill_id, version_id=version_id)


def list_skill_projections(root: str | Path | None, *, mode: str | None = None, base_url: str | None = None) -> list[dict[str, Any]]:
    return open_registry(root, mode=mode, base_url=base_url).list_skill_projections()


def find_skill_projection(
    root: str | Path | None,
    request: Any,
    *,
    mode: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return find_skill(root, request, mode=mode, base_url=base_url, **kwargs)


def execute_skill_projection(
    root: str | Path | None,
    request: Any,
    *,
    mode: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return execute_skill(root, request, mode=mode, base_url=base_url, **kwargs)


__all__ = [
    "LocalDevRegistryService",
    "build_engine_app",
    "RegistryAdapter",
    "RemoteRegistryService",
    "build_registry_app",
    "execute_skill",
    "execute_skill_projection",
    "find_skill",
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
