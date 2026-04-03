from __future__ import annotations

from pathlib import Path
from typing import Any

from .bootstrap import ensure_source_layout
from .contracts import build_source_bundle, load_skill_package, materialize_runtime_install, validate_skill_package
from .factory import build_candidate_payload, prepare_candidate_for_lab, run_factory_pipeline
from .kernel import create_kernel_engine, create_kernel_manager, get_engine_execution_meta, list_engines, list_plugins
from .lab import (
    build_promotion_submission,
    get_skill_lab_run_artifacts,
    get_skill_lab_run_status,
    init_skill_lab_project,
    run_skill_lab_project,
    validate_skill_lab_project,
)
from .models import PromotionSubmission
from .paths import PlatformPaths, detect_platform_paths
from .registry import build_registry_app, ingest_feedback, open_registry, publish_package, resolve_install_bundle, submit_promotion
from .runtime import build_runtime_install_bundle, hydrate_runtime_install, run_runtime

ensure_source_layout()


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

    def run_runtime(
        self,
        package_root: str | Path,
        *,
        action_id: str | None = None,
        action_input: Any = None,
        workspace_dir: str | Path | None = None,
        run_id: str | None = None,
        install_root: str | Path | None = None,
        env: dict[str, str] | None = None,
        max_sandbox: str | None = None,
        allow_network: bool = False,
    ) -> dict[str, Any]:
        return run_runtime(
            package_root,
            action_id=action_id,
            action_input=action_input,
            workspace_dir=workspace_dir,
            run_id=run_id,
            install_root=install_root,
            env=env,
            max_sandbox=max_sandbox,
            allow_network=allow_network,
        )

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

    def build_promotion_submission(self, project_root: str | Path, run_id: str) -> PromotionSubmission:
        return build_promotion_submission(project_root, run_id)

    def registry_root(self) -> Path:
        root = self.paths.data_root / "registry"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def registry_server_root(self) -> Path:
        return self.paths.registry_root_dir / "server"

    def build_candidate_payload(
        self,
        *,
        skill_name: str,
        workflow: dict[str, Any] | None = None,
        transcript: dict[str, Any] | None = None,
        failure: dict[str, Any] | None = None,
        owner: str = "agent-skill-platform",
    ) -> dict[str, Any]:
        return build_candidate_payload(
            skill_name=skill_name,
            workflow=workflow,
            transcript=transcript,
            failure=failure,
            owner=owner,
        )

    def prepare_candidate_for_lab(
        self,
        project_root: str | Path,
        *,
        skill_name: str,
        workflow: dict[str, Any] | None = None,
        transcript: dict[str, Any] | None = None,
        failure: dict[str, Any] | None = None,
        owner: str = "agent-skill-platform",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        return prepare_candidate_for_lab(
            project_root,
            skill_name=skill_name,
            workflow=workflow,
            transcript=transcript,
            failure=failure,
            owner=owner,
            overwrite=overwrite,
        )

    def run_factory_pipeline(
        self,
        project_root: str | Path,
        *,
        skill_name: str,
        workflow: dict[str, Any] | None = None,
        transcript: dict[str, Any] | None = None,
        failure: dict[str, Any] | None = None,
        owner: str = "agent-skill-platform",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        return run_factory_pipeline(
            project_root,
            skill_name=skill_name,
            workflow=workflow,
            transcript=transcript,
            failure=failure,
            owner=owner,
            overwrite=overwrite,
        )

    def publish_package(
        self,
        source: str | Path,
        *,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> dict[str, Any]:
        return publish_package(registry_root or self.registry_root(), source, mode=registry_mode, base_url=registry_base_url)

    def resolve_install_bundle(
        self,
        skill_id: str,
        *,
        version_id: str | None = None,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> dict[str, Any]:
        return resolve_install_bundle(
            registry_root or self.registry_root(),
            skill_id,
            version_id=version_id,
            mode=registry_mode,
            base_url=registry_base_url,
        )

    def ingest_feedback(
        self,
        envelope: Any,
        *,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> dict[str, Any]:
        return ingest_feedback(
            registry_root or self.registry_root(),
            envelope,
            mode=registry_mode,
            base_url=registry_base_url,
        )

    def submit_promotion(
        self,
        submission: PromotionSubmission | dict[str, Any],
        *,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> dict[str, Any]:
        return submit_promotion(
            registry_root or self.registry_root(),
            submission,
            mode=registry_mode,
            base_url=registry_base_url,
        )

    def build_registry_app(self, *, registry_root: str | Path | None = None) -> Any:
        return build_registry_app(registry_root or self.registry_root())

    def list_registry_skills(
        self,
        *,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> list[dict[str, Any]]:
        return open_registry(registry_root or self.registry_root(), mode=registry_mode, base_url=registry_base_url).list_skills()

    def get_registry_skill(
        self,
        skill_id: str,
        *,
        registry_root: str | Path | None = None,
        registry_mode: str | None = None,
        registry_base_url: str | None = None,
    ) -> dict[str, Any]:
        return open_registry(
            registry_root or self.registry_root(),
            mode=registry_mode,
            base_url=registry_base_url,
        ).get_skill(skill_id)

    def list_kernel_plugins(self) -> dict[str, Any]:
        return list_plugins()

    def list_kernel_engines(self) -> list[str]:
        return list_engines()

    def get_kernel_engine_execution_meta(self, name: str) -> dict[str, Any]:
        return get_engine_execution_meta(name)

    def create_kernel_manager(self, name: str | None = None, **kwargs: Any) -> Any:
        return create_kernel_manager(name=name, **kwargs)

    def create_kernel_engine(self, name: str, **kwargs: Any) -> Any:
        return create_kernel_engine(name=name, **kwargs)
