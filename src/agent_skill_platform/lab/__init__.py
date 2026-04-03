from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch_agent.cli.runtime import get_run_artifacts, get_run_status, init_project, run_project, validate_project

from ..models import PromotionSubmission


def init_skill_lab_project(
    project_root: str | Path,
    *,
    project_name: str | None = None,
    pack_id: str = "skill_research",
    data_source: str = "datasets/input.json",
    overwrite: bool = False,
) -> dict[str, Any]:
    return init_project(
        Path(project_root),
        project_name=project_name,
        pack_id=pack_id,
        data_source=data_source,
        overwrite=overwrite,
    )


def validate_skill_lab_project(project_root: str | Path) -> dict[str, Any]:
    return validate_project(Path(project_root))


def run_skill_lab_project(project_root: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    return run_project(Path(project_root), run_id=run_id)


def get_skill_lab_run_status(project_root: str | Path, run_id: str) -> dict[str, Any]:
    return get_run_status(Path(project_root), run_id)


def get_skill_lab_run_artifacts(project_root: str | Path, run_id: str) -> list[dict[str, Any]]:
    return get_run_artifacts(Path(project_root), run_id)


def build_promotion_submission(project_root: str | Path, run_id: str) -> PromotionSubmission:
    return PromotionSubmission.from_skill_lab_run(Path(project_root), run_id)


__all__ = [
    "build_promotion_submission",
    "get_skill_lab_run_artifacts",
    "get_skill_lab_run_status",
    "init_skill_lab_project",
    "run_skill_lab_project",
    "validate_skill_lab_project",
]
