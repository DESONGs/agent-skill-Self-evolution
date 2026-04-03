from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import build_source_bundle, load_skill_package, materialize_runtime_install, validate_skill_package
from .lab import (
    build_promotion_submission,
    get_skill_lab_run_artifacts,
    get_skill_lab_run_status,
    init_skill_lab_project,
    run_skill_lab_project,
    validate_skill_lab_project,
)
from .paths import PlatformPaths, detect_platform_paths
from .runtime import build_runtime_install_bundle, hydrate_runtime_install


class AgentSkillPlatform:
    def __init__(self, paths: PlatformPaths | None = None):
        self.paths = paths or detect_platform_paths()
        self.paths.ensure_exists()

    def validate_package(self, package_root: str | Path, action_id: str | None = None) -> Any:
        return validate_skill_package(package_root, action_id=action_id)

    def load_package(self, package_root: str | Path) -> Any:
        return load_skill_package(package_root)

    def bundle_source_package(self, package_root: str | Path, output_dir: str | Path) -> Any:
        return build_source_bundle(package_root, output_dir)

    def materialize_package_runtime(self, package_root: str | Path, exec_dir: str | Path, compat_root: str = ".claude/skills") -> Any:
        return materialize_runtime_install(package_root, exec_dir, compat_root=compat_root)

    def build_install_bundle(self, package_root: str | Path, *, skill_id: str | None = None, version_id: str | None = None) -> Any:
        return build_runtime_install_bundle(package_root, skill_id=skill_id, version_id=version_id)

    def hydrate_install(self, package_root: str | Path, *, install_root: str | Path, install_id: str | None = None) -> Any:
        return hydrate_runtime_install(package_root, install_root=install_root, install_id=install_id)

    def init_skill_lab_project(self, project_root: str | Path, *, project_name: str | None = None, overwrite: bool = False) -> dict[str, Any]:
        return init_skill_lab_project(project_root, project_name=project_name, overwrite=overwrite)

    def validate_skill_lab_project(self, project_root: str | Path) -> dict[str, Any]:
        return validate_skill_lab_project(project_root)

    def run_skill_lab_project(self, project_root: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
        return run_skill_lab_project(project_root, run_id=run_id)

    def get_skill_lab_run_status(self, project_root: str | Path, run_id: str) -> dict[str, Any]:
        return get_skill_lab_run_status(project_root, run_id)

    def get_skill_lab_run_artifacts(self, project_root: str | Path, run_id: str) -> list[dict[str, Any]]:
        return get_skill_lab_run_artifacts(project_root, run_id)

    def build_promotion_submission(self, project_root: str | Path, run_id: str):
        return build_promotion_submission(project_root, run_id)
