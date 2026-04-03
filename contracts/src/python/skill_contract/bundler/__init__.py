from __future__ import annotations

from pathlib import Path

from skill_contract.bundler.contracts import (
    AdapterArtifact,
    BundleArtifact,
    ContractLoadError,
    ContractValidationError,
    ExportManifestArtifact,
    RuntimeInstallArtifact,
    SkillPackage,
    ValidationIssue,
    ValidationReport,
    validate_skill_package,
)
from skill_contract.bundler.export_manifest import build_export_manifest
from skill_contract.bundler.runtime_install import materialize_runtime_install
from skill_contract.bundler.source_bundle import build_source_bundle


def build_target_bundle(
    package_root: Path | str,
    output_dir: Path | str,
    platform: str,
    package: SkillPackage | None = None,
) -> AdapterArtifact:
    from skill_contract.bundler.target_bundle import build_target_bundle as _build_target_bundle

    return _build_target_bundle(package_root, output_dir, platform, package=package)


__all__ = [
    "AdapterArtifact",
    "BundleArtifact",
    "ContractLoadError",
    "ContractValidationError",
    "ExportManifestArtifact",
    "RuntimeInstallArtifact",
    "SkillPackage",
    "ValidationIssue",
    "ValidationReport",
    "validate_skill_package",
    "build_export_manifest",
    "build_source_bundle",
    "build_target_bundle",
    "materialize_runtime_install",
]
