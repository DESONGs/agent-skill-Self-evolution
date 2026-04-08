from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_contract.bundler.runtime_install import materialize_runtime_install as _materialize_runtime_install
from skill_contract.bundler.source_bundle import build_source_bundle as _build_source_bundle
from skill_contract.parsers.package import load_skill_package as _load_skill_package
from skill_contract.validators.package import validate_skill_package as _validate_skill_package


def validate_skill_package(package_root: str | Path, action_id: str | None = None) -> Any:
    return _validate_skill_package(Path(package_root), action_id=action_id)


def load_skill_package(package_root: str | Path) -> Any:
    return _load_skill_package(Path(package_root))


def build_source_bundle(package_root: str | Path, output_dir: str | Path) -> Any:
    return _build_source_bundle(Path(package_root), Path(output_dir))


def materialize_runtime_install(package_root: str | Path, exec_dir: str | Path, compat_root: str = ".claude/skills") -> Any:
    return _materialize_runtime_install(Path(package_root), Path(exec_dir), compat_root=compat_root)


__all__ = [
    "build_source_bundle",
    "load_skill_package",
    "materialize_runtime_install",
    "validate_skill_package",
]
