"""Run context management for isolated execution."""

import asyncio
import hashlib
import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import PROJECT_ROOT
from orchestrator.runtime.envelope import ArtifactRecord, ResultEnvelope, RunEnvelope
from orchestrator.runtime.install import SkillInstall, load_local_skill_package

logger = logging.getLogger(__name__)

DEFAULT_COMPAT_ROOT = ".claude/skills"


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _artifact_records_from_result(result: dict[str, Any]) -> list[ArtifactRecord]:
    raw_artifacts = result.get("artifacts") or []
    artifacts: list[ArtifactRecord] = []
    for index, item in enumerate(raw_artifacts):
        if isinstance(item, ArtifactRecord):
            artifacts.append(item)
        elif isinstance(item, dict):
            artifacts.append(ArtifactRecord.from_dict(item))
        else:
            artifacts.append(
                ArtifactRecord(
                    artifact_id=f"artifact-{index + 1}",
                    path=str(item),
                )
            )
    return artifacts


def _install_lookup_keys(install: SkillInstall) -> tuple[str, ...]:
    return (
        install.package.bundle.skill_id,
        install.package.root.name,
        install.install_id,
        install.mounted_path.name,
    )


class RunContext:
    """Manage isolated environment for single execution.

    Uses a dual-directory architecture:
    - exec_dir: Temporary directory in /tmp for CLI execution (isolated from AgentSkillOS)
    - run_dir:  Permanent directory in runs/ for metadata, logs, and final results

    The exec_dir is placed in system temp to break all ancestor relationships
    with AgentSkillOS, preventing CLI from discovering parent .claude/ via
    upward directory traversal.
    """

    def __init__(self, run_id: str, base_dir: Path, compat_root: str = DEFAULT_COMPAT_ROOT):
        self.run_id = run_id
        self.run_dir = base_dir / run_id          # Permanent storage (meta, logs, final results)
        self.compat_root = compat_root.strip("/").strip() or DEFAULT_COMPAT_ROOT

        # Isolated temp directory for CLI execution.
        # Placed in system temp to break all ancestor relationships
        # with AgentSkillOS, preventing CLI from discovering parent .claude/.
        self._exec_root = Path(tempfile.mkdtemp(prefix=f"aso-{run_id[:20]}-"))
        self.exec_dir = self._exec_root           # CLI subprocess cwd

        self.runtime_install_root = self.exec_dir / self.compat_root
        self.skills_dir = self.runtime_install_root                  # Skills in exec dir
        self.workspace_dir = self.exec_dir / "workspace"             # Workspace in exec dir
        self.logs_dir = self.run_dir / "logs"                        # Logs in permanent dir
        self.artifacts_dir = self.run_dir / "artifacts"
        self.installs_dir = self.run_dir / "installs"
        self.meta_path = self.run_dir / "meta.json"
        self.result_path = self.run_dir / "result.json"
        self.plan_path = self.run_dir / "plan.json"
        self.environment_path = self.run_dir / "environment.json"
        self.retrieval_path = self.run_dir / "retrieval.json"
        self.run_envelope_path = self.run_dir / "run_envelope.json"
        self.result_envelope_path = self.run_dir / "result_envelope.json"
        self.installs_path = self.run_dir / "installs.json"
        self.artifact_index_path = self.run_dir / "artifact_index.json"
        self.feedback_path = self.run_dir / "feedback.json"
        self.feedback_outbox_dir = self.run_dir / "feedback_outbox"
        self.installs: list[SkillInstall] = []
        self._installs_by_key: dict[str, SkillInstall] = {}
        self._run_envelope: RunEnvelope | None = None
        self._setup_done = False
        self._finalized = False

    @classmethod
    def create(
        cls,
        task: str,
        base_dir: str = "runs",
        mode: str = None,
        task_name: str = None,
        task_id: str = None,
        compat_root: str = DEFAULT_COMPAT_ROOT,
    ) -> "RunContext":
        """Create a new execution context.

        Args:
            task: Task description for generating hash
            base_dir: Path to runs directory
            mode: Execution mode (dag, free-style, auto_selected, auto_all, baseline)
            task_name: User-specified task name (optional)
            task_id: Task identifier for batch execution (optional)

        Returns:
            RunContext instance
        """
        import re
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_hash = hashlib.md5(task.encode()).hexdigest()[:6]

        parts = [timestamp]
        if mode:
            parts.append(mode)
        # Prefer task_id over task_name for naming (task_id is more structured)
        if task_id:
            safe_id = cls._sanitize_name(task_id)
            if safe_id:
                parts.append(safe_id)
        elif task_name:
            safe_name = cls._sanitize_name(task_name)
            if safe_name:
                parts.append(safe_name)
        parts.append(task_hash)

        run_id = "-".join(parts)
        return cls(run_id, Path(base_dir), compat_root=compat_root)

    @staticmethod
    def _sanitize_name(name: str, max_length: int = 30) -> str:
        """Sanitize task name for safe folder naming.

        Args:
            name: Raw task name
            max_length: Maximum length of sanitized name

        Returns:
            Sanitized name safe for use in folder names
        """
        import re
        sanitized = name.replace(" ", "_")
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)
        sanitized = sanitized.lower()[:max_length].rstrip('_-')
        return sanitized

    def get_runtime_install_path(self, skill_name: str) -> Path:
        """Return the runtime install path for a skill slug."""
        return self.runtime_install_root / skill_name

    def list_installs(self) -> list[SkillInstall]:
        """Return the hydrated installs currently available to the run."""
        return list(self.installs)

    def get_install(self, skill_id: str) -> SkillInstall | None:
        """Return a hydrated install by skill id, package name, or install id."""
        if skill_id in self._installs_by_key:
            return self._installs_by_key[skill_id]
        for install in self.installs:
            if skill_id in _install_lookup_keys(install):
                self._installs_by_key[skill_id] = install
                return install
        return None

    def _register_install(self, install: SkillInstall) -> None:
        self.installs.append(install)
        for key in _install_lookup_keys(install):
            self._installs_by_key[key] = install

    def _write_installs_manifest(self) -> None:
        _json_write(self.installs_path, [install.to_dict() for install in self.installs])

    def _write_environment_manifest(self) -> None:
        payload = {
            "run_id": self.run_id,
            "compat_root": self.compat_root,
            "exec_dir": str(self.exec_dir),
            "run_dir": str(self.run_dir),
            "workspace_dir": str(self.workspace_dir),
            "skills_dir": str(self.skills_dir),
            "logs_dir": str(self.logs_dir),
        }
        _json_write(self.environment_path, payload)

    def _write_retrieval_manifest(self, task: str, mode: str, skills: list[str], copy_all: bool, task_id: str | None) -> None:
        payload = {
            "run_id": self.run_id,
            "task": task,
            "mode": mode,
            "skills": list(skills),
            "copy_all_skills": copy_all,
            "task_id": task_id,
            "selected_install_ids": [install.install_id for install in self.installs],
        }
        _json_write(self.retrieval_path, payload)

    def _write_run_envelope(self, task: str, mode: str, skills: list[str], task_id: str | None, copy_all: bool) -> None:
        envelope = RunEnvelope(
            run_id=self.run_id,
            task=task,
            mode=mode,
            selected_skills=list(skills),
            copy_all_skills=copy_all,
            run_dir=self.run_dir,
            exec_dir=self.exec_dir,
            workspace_dir=self.workspace_dir,
            logs_dir=self.logs_dir,
            skills_dir=self.skills_dir,
            installs=[install.to_dict() for install in self.installs],
            metadata={
                "task_id": task_id,
                "compat_root": self.compat_root,
                "selected_install_ids": [install.install_id for install in self.installs],
            },
        )
        self._run_envelope = envelope
        _json_write(self.run_envelope_path, envelope.to_dict())

    def _hydrate_skill_package(
        self,
        source_skill_dir: Path,
        install_name: str | None = None,
        include_evals: bool = False,
        include_adapters: bool = False,
    ) -> SkillInstall:
        if not source_skill_dir.exists():
            raise FileNotFoundError(f"Skill source not found: {source_skill_dir}")

        package = load_local_skill_package(source_skill_dir)
        skill_id = install_name or package.bundle.skill_id or source_skill_dir.name
        install_id = f"{skill_id}-{package.bundle.bundle_sha256[:12]}"

        install_root = self.installs_dir / install_id
        if install_root.exists():
            shutil.rmtree(install_root)
        install_root.mkdir(parents=True, exist_ok=True)

        copied_files: list[str] = []
        for filename in ("SKILL.md", "manifest.json", "actions.yaml"):
            candidate = source_skill_dir / filename
            if candidate.is_file():
                shutil.copy2(candidate, install_root / filename)
                copied_files.append(filename)

        for dirname in ("agents", "references", "scripts", "assets"):
            candidate = source_skill_dir / dirname
            if candidate.is_dir():
                shutil.copytree(candidate, install_root / dirname, dirs_exist_ok=True)
                copied_files.extend(
                    path.relative_to(install_root).as_posix()
                    for path in install_root.joinpath(dirname).rglob("*")
                    if path.is_file()
                )

        if include_evals:
            candidate = source_skill_dir / "evals"
            if candidate.is_dir():
                shutil.copytree(candidate, install_root / "evals", dirs_exist_ok=True)
                copied_files.extend(
                    path.relative_to(install_root).as_posix()
                    for path in install_root.joinpath("evals").rglob("*")
                    if path.is_file()
                )

        if include_adapters:
            candidate = source_skill_dir / "adapters"
            if candidate.is_dir():
                shutil.copytree(candidate, install_root / "adapters", dirs_exist_ok=True)
                copied_files.extend(
                    path.relative_to(install_root).as_posix()
                    for path in install_root.joinpath("adapters").rglob("*")
                    if path.is_file()
                )

        mounted_path = self.runtime_install_root / skill_id
        if mounted_path.exists():
            shutil.rmtree(mounted_path)
        mounted_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(install_root, mounted_path)

        install = SkillInstall(
            install_id=install_id,
            package=package,
            install_root=install_root,
            mounted_path=mounted_path,
            copied_files=tuple(sorted(dict.fromkeys(copied_files))),
            mode="run",
            selected_action=package.bundle.default_action,
            metadata={
                "source_skill_dir": str(source_skill_dir),
                "skill_id": skill_id,
            },
        )
        return install

    def materialize_skill_install(
        self,
        source_skill_dir: Path,
        install_name: str | None = None,
        include_evals: bool = False,
        include_adapters: bool = False,
    ) -> Path:
        """Copy a skill package into the runtime install root."""
        install = self._hydrate_skill_package(
            source_skill_dir,
            install_name=install_name,
            include_evals=include_evals,
            include_adapters=include_adapters,
        )
        self._register_install(install)
        self._write_installs_manifest()
        return install.mounted_path

    def setup(
        self,
        skill_names: list[str],
        source_skill_dir: Path,
        copy_all: bool = False,
    ) -> None:
        """Initialize directory structures and copy skills.

        Sets up two directories:
        - exec_dir (temp): isolated CLI environment with workspace and skills
        - run_dir (permanent): logs and metadata only (workspace copied back after execution)

        Args:
            skill_names: List of skill names to copy
            source_skill_dir: Source skill directory (usually .claude/skills)
            copy_all: If True, copy all skills; otherwise only copy skill_names
        """
        if self._setup_done:
            return

        # Permanent dir: logs only (meta.json/result.json/plan.json written separately)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.installs_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Exec dir: workspace only (no git init, no settings.json needed).
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Copy .env to exec_dir so CLI subprocess / skills can access API keys
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            shutil.copy2(env_file, self.exec_dir / ".env")

        if copy_all:
            # Copy all skills
            if source_skill_dir.exists():
                for skill_dir in source_skill_dir.iterdir():
                    if skill_dir.is_dir():
                        self._register_install(
                            self._hydrate_skill_package(skill_dir, install_name=skill_dir.name)
                        )
        elif skill_names:
            # Copy only specified skills
            for name in skill_names:
                src = source_skill_dir / name
                if src.exists():
                    self._register_install(self._hydrate_skill_package(src, install_name=name))
        # If skill_names is empty and copy_all is False, don't create a runtime install tree.

        self._write_installs_manifest()
        self._setup_done = True

    def copy_files(self, file_paths: list[str]) -> list[str]:
        """Copy specified files to workspace directory.

        Args:
            file_paths: List of file paths (supports absolute and relative paths)

        Returns:
            List of successfully copied filenames
        """
        copied = []
        for path_str in file_paths:
            src = Path(path_str).expanduser().resolve()
            if not src.exists():
                continue
            dst = self.workspace_dir / src.name
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            copied.append(src.name)
        return copied

    def save_meta(
        self,
        task: str,
        mode: str,
        skills: list[str],
        task_id: str = None,
        copy_all: bool = False,
    ) -> None:
        """Save execution metadata.

        Args:
            task: Task description
            mode: Execution mode
            skills: List of used skills
            task_id: Task identifier (for batch execution)
            copy_all: If True, indicates all skills were copied to exec env
        """
        meta = {
            "run_id": self.run_id,
            "task": task,
            "mode": mode,
            "skills": skills,
            "skills_copy_all": copy_all,
            "started_at": datetime.now().isoformat(),
        }
        if task_id:
            meta["task_id"] = task_id
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self._write_environment_manifest()
        self._write_retrieval_manifest(task=task, mode=mode, skills=skills, copy_all=copy_all, task_id=task_id)
        self._write_run_envelope(task=task, mode=mode, skills=skills, task_id=task_id, copy_all=copy_all)
        self._write_installs_manifest()

    def update_meta(self, **kwargs) -> None:
        """Update metadata fields.

        Args:
            **kwargs: Fields to update
        """
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {}

        meta.update(kwargs)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def save_result(self, result: dict) -> None:
        """Save execution result.

        Args:
            result: Execution result dictionary
        """
        # Also update completed_at in meta.json
        self.update_meta(completed_at=datetime.now().isoformat())

        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        result_envelope = ResultEnvelope(
            run_id=str(result.get("run_id", self.run_id)),
            status=str(result.get("status", "completed")),
            summary=str(result.get("summary", "")),
            error=result.get("error"),
            mode=str(result.get("mode", "")),
            started_at=str(result.get("started_at", datetime.now().isoformat())),
            completed_at=str(result.get("completed_at", datetime.now().isoformat())),
            selected_skills=list(result.get("selected_skills", []) or []),
            actions_executed=list(result.get("actions_executed", []) or []),
            artifacts=_artifact_records_from_result(result),
            metrics=dict(result.get("metrics", {}) or {}),
            metadata=dict(result.get("metadata", {}) or {}),
        )
        _json_write(self.result_envelope_path, result_envelope.to_dict())

        artifact_index = {
            "run_id": self.run_id,
            "artifacts": [artifact.to_dict() for artifact in result_envelope.artifacts],
        }
        _json_write(self.artifact_index_path, artifact_index)

    def save_plan(self, plan: dict) -> None:
        """Save execution plan.

        Args:
            plan: Execution plan dictionary
        """
        with open(self.plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

    def get_log_path(self, name: str) -> Path:
        """Get path for a log file.

        Args:
            name: Log file name (without extension)

        Returns:
            Path to the log file in logs_dir
        """
        # Ensure logs_dir exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        return self.logs_dir / f"{name}.log"

    def finalize(self) -> None:
        """Copy workspace results from exec dir to permanent storage, then clean up.

        Should be called after execution completes (in engine finally blocks).
        Copies the entire exec_dir to the permanent run_dir (preserving
        workspace, .claude/skills, and any other files), then removes the
        temp directory.

        Idempotent: safe to call multiple times (e.g. from both normal flow
        and a finally block).
        """
        if self._finalized:
            return
        self._finalized = True

        try:
            if self._exec_root.exists():
                shutil.copytree(self._exec_root, self.run_dir, dirs_exist_ok=True)
        except Exception:
            # Copy failed — keep temp dir so data can be recovered manually
            logger.warning(
                "Failed to copy exec_dir from %s to %s; "
                "temp directory preserved for recovery",
                self._exec_root, self.run_dir,
                exc_info=True,
            )
            return
        # Clean up temp dir only after successful copy
        shutil.rmtree(self._exec_root, ignore_errors=True)

    def __del__(self) -> None:
        """Safety net: clean up temp directory if finalize() was never called."""
        try:
            if not self._finalized and self._exec_root.exists():
                shutil.rmtree(self._exec_root, ignore_errors=True)
        except Exception:
            pass

    # ----- async wrappers (delegate to thread to avoid blocking event loop) -----

    async def async_setup(self, *args, **kwargs) -> None:
        await asyncio.to_thread(self.setup, *args, **kwargs)

    async def async_copy_files(self, *args, **kwargs) -> list[str]:
        return await asyncio.to_thread(self.copy_files, *args, **kwargs)

    async def async_save_meta(self, *args, **kwargs) -> None:
        await asyncio.to_thread(self.save_meta, *args, **kwargs)

    async def async_save_result(self, *args, **kwargs) -> None:
        await asyncio.to_thread(self.save_result, *args, **kwargs)

    async def async_finalize(self) -> None:
        """Async wrapper for finalize()."""
        await asyncio.to_thread(self.finalize)
