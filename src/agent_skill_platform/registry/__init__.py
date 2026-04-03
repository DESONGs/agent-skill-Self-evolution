from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from ..models import PromotionSubmission
from .api import create_registry_app
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


def build_registry_app(root: str | Path) -> FastAPI:
    return create_registry_app(root)


def list_skills(root: str | Path) -> list[dict[str, Any]]:
    return RegistryService(root).list_skills()


def get_skill(root: str | Path, skill_id: str) -> dict[str, Any]:
    return RegistryService(root).get_skill(skill_id)


__all__ = [
    "RegistryService",
    "build_registry_app",
    "get_skill",
    "ingest_feedback",
    "list_skills",
    "open_registry",
    "publish_package",
    "resolve_install_bundle",
    "submit_promotion",
]
