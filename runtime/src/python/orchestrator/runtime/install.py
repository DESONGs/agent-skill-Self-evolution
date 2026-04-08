"""Runtime install bundle and local skill install contracts.

This module models the hydration boundary between a skill package/bundle and
the isolated run-time copy that the orchestrator executes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .actions import ActionManifest, parse_actions_yaml
from .profiles import infer_skill_type, normalize_skill_type


class InstallContractError(ValueError):
    """Raised when a skill install or bundle contract is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_dir(root: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = file_path.relative_to(root).as_posix().encode("utf-8")
        digest.update(rel)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _read_manifest_version(root: Path) -> str | None:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = payload.get("version")
    return str(version) if version else None


def _read_manifest_payload(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class RuntimeInstallBundle:
    """Registry-facing install payload, resolved locally for runtime use."""

    skill_id: str
    version_id: str | None
    bundle_root: Path
    bundle_sha256: str
    bundle_size: int
    actions: ActionManifest
    skill_type: str = "script"
    default_action: str | None = None
    source_uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_package_root(
        cls,
        package_root: str | Path,
        *,
        skill_id: str | None = None,
        version_id: str | None = None,
        strict_actions: bool = True,
    ) -> "RuntimeInstallBundle":
        root = Path(package_root)
        if not root.exists():
            raise InstallContractError(f"Package root does not exist: {root}")

        skill_md = root / "SKILL.md"
        if not skill_md.exists():
            raise InstallContractError(f"Missing SKILL.md in package root: {root}")

        actions_path = root / "actions.yaml"
        if not actions_path.exists():
            compat_note = ""
            if not strict_actions:
                compat_note = (
                    " strict_actions=False is metadata-only compatibility and does not "
                    "permit install-time action fallback."
                )
            raise InstallContractError(f"Missing actions.yaml in package root: {root}.{compat_note}")

        actions = parse_actions_yaml(actions_path)
        manifest_payload = _read_manifest_payload(root)
        inferred_skill_type = infer_skill_type(manifest_payload, actions.actions)

        inferred_skill_id = skill_id or root.name
        inferred_version_id = version_id or _read_manifest_version(root)
        inferred_bundle_size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        bundle = cls(
            skill_id=inferred_skill_id,
            version_id=inferred_version_id,
            bundle_root=root,
            bundle_sha256=_sha256_dir(root),
            bundle_size=inferred_bundle_size,
            actions=actions,
            skill_type=normalize_skill_type(inferred_skill_type),
            default_action=actions.default_action or (actions.action_ids()[0] if actions.actions else None),
            source_uri=str(root),
            metadata={
                "created_at": _utc_now(),
                "manifest_version": inferred_version_id,
                "actions_contract_required": True,
                "skill_type": normalize_skill_type(inferred_skill_type),
            },
        )
        bundle.validate()
        return bundle

    def validate(self) -> None:
        if not self.skill_id:
            raise InstallContractError("skill_id must be non-empty")
        if not self.bundle_root.exists():
            raise InstallContractError(f"bundle_root does not exist: {self.bundle_root}")
        self.actions.validate(package_root=self.bundle_root)
        if self.default_action is not None and not self.actions.has(self.default_action):
            raise InstallContractError(
                f"default_action {self.default_action!r} is not declared in the manifest"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "version_id": self.version_id,
            "bundle_root": str(self.bundle_root),
            "bundle_sha256": self.bundle_sha256,
            "bundle_size": self.bundle_size,
            "skill_type": self.skill_type,
            "default_action": self.default_action,
            "source_uri": self.source_uri,
            "actions": self.actions.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LocalSkillPackage:
    """A local, validated skill package on disk."""

    root: Path
    skill_md: Path
    actions_path: Path
    bundle: RuntimeInstallBundle
    manifest_path: Path | None = None
    files: tuple[Path, ...] = field(default_factory=tuple)

    @classmethod
    def from_root(
        cls,
        root: str | Path,
        *,
        strict_actions: bool = True,
    ) -> "LocalSkillPackage":
        package_root = Path(root)
        if not package_root.exists():
            raise InstallContractError(f"Package root does not exist: {package_root}")

        skill_md = package_root / "SKILL.md"
        if not skill_md.exists():
            raise InstallContractError(f"Missing SKILL.md in package root: {package_root}")

        actions_path = package_root / "actions.yaml"
        if not actions_path.exists():
            compat_note = ""
            if not strict_actions:
                compat_note = (
                    " strict_actions=False is metadata-only compatibility and does not "
                    "permit install-time action fallback."
                )
            raise InstallContractError(
                f"Missing actions.yaml in package root: {package_root}.{compat_note}"
            )

        bundle = RuntimeInstallBundle.from_package_root(
            package_root,
            skill_id=package_root.name,
            strict_actions=strict_actions,
        )
        manifest_path = package_root / "manifest.json"
        files = tuple(sorted(p for p in package_root.rglob("*") if p.is_file()))
        return cls(
            root=package_root,
            skill_md=skill_md,
            actions_path=actions_path,
            bundle=bundle,
            manifest_path=manifest_path if manifest_path.exists() else None,
            files=files,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "skill_md": str(self.skill_md),
            "actions_path": str(self.actions_path),
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "bundle": self.bundle.to_dict(),
            "files": [str(p) for p in self.files],
        }


@dataclass(frozen=True)
class SkillInstall:
    """Run-specific hydrated copy of a local skill package."""

    install_id: str
    package: LocalSkillPackage
    install_root: Path
    mounted_path: Path
    skill_type: str = "script"
    copied_files: tuple[str, ...] = field(default_factory=tuple)
    created_at: str = field(default_factory=_utc_now)
    mode: str = "run"
    selected_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "install_id": self.install_id,
            "package": self.package.to_dict(),
            "install_root": str(self.install_root),
            "mounted_path": str(self.mounted_path),
            "skill_type": self.skill_type,
            "copied_files": list(self.copied_files),
            "created_at": self.created_at,
            "mode": self.mode,
            "selected_action": self.selected_action,
            "metadata": dict(self.metadata),
        }

    @property
    def action_manifest(self) -> ActionManifest:
        return self.package.bundle.actions

    def resolve_action(self, action_id: str | None = None):
        candidate_id = action_id or self.package.bundle.default_action
        if not candidate_id:
            raise InstallContractError("No action id available for this install")
        return self.action_manifest.get(candidate_id)


def hydrate_skill_install(
    package: str | Path | LocalSkillPackage,
    *,
    install_root: str | Path,
    install_id: str | None = None,
    strict_actions: bool = True,
    copy_tree: bool = True,
) -> SkillInstall:
    """Materialize a local package into a run-scoped install directory."""

    local_package = package if isinstance(package, LocalSkillPackage) else LocalSkillPackage.from_root(
        package,
        strict_actions=strict_actions,
    )

    base_root = Path(install_root)
    base_root.mkdir(parents=True, exist_ok=True)
    final_install_id = install_id or f"{local_package.root.name}-{local_package.bundle.bundle_sha256[:12]}"
    install_dir = base_root / final_install_id
    if install_dir.exists():
        shutil.rmtree(install_dir)

    if copy_tree:
        shutil.copytree(local_package.root, install_dir)
    else:
        install_dir.mkdir(parents=True, exist_ok=True)

    mounted_path = install_dir / ".claude" / "skills" / local_package.root.name
    mounted_path.parent.mkdir(parents=True, exist_ok=True)
    if not mounted_path.exists():
        shutil.copytree(local_package.root, mounted_path)

    copied_files = tuple(
        sorted(p.relative_to(install_dir).as_posix() for p in install_dir.rglob("*") if p.is_file())
    )

    install = SkillInstall(
        install_id=final_install_id,
        package=local_package,
        install_root=install_dir,
        mounted_path=mounted_path,
        skill_type=normalize_skill_type(local_package.bundle.skill_type),
        copied_files=copied_files,
        metadata={
            "bundle_sha256": local_package.bundle.bundle_sha256,
            "bundle_size": local_package.bundle.bundle_size,
            "version_id": local_package.bundle.version_id,
            "default_action": local_package.bundle.default_action,
            "skill_type": normalize_skill_type(local_package.bundle.skill_type),
        },
    )
    return install


def load_local_skill_package(root: str | Path, *, strict_actions: bool = True) -> LocalSkillPackage:
    """Convenience loader for local package roots."""

    return LocalSkillPackage.from_root(root, strict_actions=strict_actions)
