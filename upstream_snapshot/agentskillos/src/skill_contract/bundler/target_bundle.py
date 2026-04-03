from __future__ import annotations

from pathlib import Path

from skill_contract.adapters import build_claude_adapter, build_generic_adapter, build_openai_adapter
from skill_contract.bundler.contracts import AdapterArtifact, SkillPackage, validate_skill_package


def build_target_bundle(
    package_root: Path | str,
    output_dir: Path | str,
    platform: str,
    package: SkillPackage | None = None,
) -> AdapterArtifact:
    package_obj = package or SkillPackage.from_root(package_root)
    validate_skill_package(package_obj).raise_for_failures()

    output_path = Path(output_dir).resolve()
    target_root = output_path / "targets" / platform
    target_root.mkdir(parents=True, exist_ok=True)

    if platform == "openai":
        return build_openai_adapter(package_obj, target_root)
    if platform == "claude":
        return build_claude_adapter(package_obj, target_root)
    if platform == "generic":
        return build_generic_adapter(package_obj, target_root)
    raise ValueError(f"Unsupported platform: {platform}")

