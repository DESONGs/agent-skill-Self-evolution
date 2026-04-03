from __future__ import annotations

import shutil
from pathlib import Path

from skill_contract.bundler.contracts import (
    RuntimeInstallArtifact,
    SkillPackage,
    copy_tree_with_excludes,
    validate_skill_package,
)


def materialize_runtime_install(
    package_root: Path | str,
    exec_dir: Path | str,
    compat_root: str = ".claude/skills",
    package: SkillPackage | None = None,
) -> RuntimeInstallArtifact:
    package_obj = package or SkillPackage.from_root(package_root)
    validate_skill_package(package_obj).raise_for_failures()

    exec_path = Path(exec_dir).resolve()
    install_root = exec_path / compat_root / package_obj.slug
    if install_root.exists():
        shutil.rmtree(install_root)
    install_root.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for entry_name in ("SKILL.md", "manifest.json", "actions.yaml"):
        source = package_obj.root / entry_name
        destination = install_root / entry_name
        shutil.copy2(source, destination)
        copied.append(entry_name)

    for dirname in ("agents", "references", "scripts", "assets"):
        source = package_obj.root / dirname
        if source.exists():
            copied.extend(
                f"{dirname}/{relative}"
                for relative in copy_tree_with_excludes(source, install_root / dirname, excludes=set())
            )

    return RuntimeInstallArtifact(
        root=install_root,
        slug=package_obj.slug,
        compat_root=compat_root,
        copied_files=tuple(copied),
    )
