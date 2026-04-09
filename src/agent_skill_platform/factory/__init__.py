from __future__ import annotations

from pathlib import Path
from typing import Any

from ..bootstrap import ensure_source_layout

ensure_source_layout()

from skill_factory import build_candidate_payload as _build_candidate_payload
from skill_factory import prepare_candidate_for_lab as _prepare_candidate_for_lab
from skill_factory import run_factory_pipeline as _run_factory_pipeline


def build_candidate_payload(
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
) -> dict[str, Any]:
    return _build_candidate_payload(
        skill_name=skill_name,
        workflow=workflow,
        transcript=transcript,
        failure=failure,
        owner=owner,
    )


def prepare_candidate_for_lab(
    project_root: str | Path,
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
    overwrite: bool = True,
) -> dict[str, Any]:
    return _prepare_candidate_for_lab(
        project_root,
        skill_name=skill_name,
        workflow=workflow,
        transcript=transcript,
        failure=failure,
        owner=owner,
        overwrite=overwrite,
    )


def run_factory_pipeline(
    project_root: str | Path,
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
    overwrite: bool = True,
) -> dict[str, Any]:
    return _run_factory_pipeline(
        project_root,
        skill_name=skill_name,
        workflow=workflow,
        transcript=transcript,
        failure=failure,
        owner=owner,
        overwrite=overwrite,
    )


__all__ = [
    "build_candidate_payload",
    "prepare_candidate_for_lab",
    "run_factory_pipeline",
]
