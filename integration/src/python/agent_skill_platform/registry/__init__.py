from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from ..bootstrap import ensure_source_layout
from ..models import PromotionSubmission
from .adapter import RegistryAdapter, RemoteRegistryService
from .api import create_registry_app
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


def build_registry_app(root: str | Path) -> FastAPI:
    return create_registry_app(root)


def list_skills(root: str | Path | None, *, mode: str | None = None, base_url: str | None = None) -> list[dict[str, Any]]:
    return open_registry(root, mode=mode, base_url=base_url).list_skills()


def get_skill(root: str | Path | None, skill_id: str, *, mode: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    return open_registry(root, mode=mode, base_url=base_url).get_skill(skill_id)


__all__ = [
    "LocalDevRegistryService",
    "RegistryAdapter",
    "RemoteRegistryService",
    "build_registry_app",
    "get_skill",
    "ingest_feedback",
    "list_skills",
    "open_registry",
    "publish_package",
    "resolve_install_bundle",
    "submit_promotion",
]
