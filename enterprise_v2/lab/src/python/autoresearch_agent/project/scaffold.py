from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch_agent.core.packs.project import create_project_scaffold


def build_project_scaffold(
    project_root: str | Path,
    *,
    project_name: str | None = None,
    pack_id: str = "prediction_market",
    data_source: str = "./datasets/input.json",
    overwrite: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)
    if root.exists() and not root.is_dir():
        raise NotADirectoryError(f"project root is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)

    config_path = root / "research.yaml"
    if config_path.exists() and not overwrite:
        raise FileExistsError(f"research.yaml already exists: {config_path}")

    created = create_project_scaffold(
        root,
        project_name=project_name or root.name,
        pack_id=pack_id,
        data_source=data_source,
    )
    created_paths = list(created.values())
    return {
        "project_root": root.resolve(),
        "config_path": config_path,
        "created_paths": created_paths,
    }


def scaffold_project(
    project_root: str | Path,
    *,
    project_name: str | None = None,
    pack_id: str = "prediction_market",
    data_source: str = "./datasets/input.json",
    overwrite: bool = False,
) -> dict[str, Any]:
    return build_project_scaffold(
        project_root,
        project_name=project_name,
        pack_id=pack_id,
        data_source=data_source,
        overwrite=overwrite,
    )

