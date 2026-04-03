from __future__ import annotations

from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile

from skill_contract.bundler.contracts import (
    BundleArtifact,
    ContractValidationError,
    SkillPackage,
    build_bundle_sha256,
    validate_skill_package,
)


def build_source_bundle(
    package_root: Path | str,
    output_dir: Path | str,
    package: SkillPackage | None = None,
) -> BundleArtifact:
    package_obj = package or SkillPackage.from_root(package_root)
    validate_skill_package(package_obj).raise_for_failures()

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    bundle_path = output_path / f"{package_obj.slug}.zip"
    included_files = tuple(_bundle_file_paths(package_obj))
    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in included_files:
            archive.write(file_path, arcname=str(file_path.relative_to(package_obj.root.parent)))

    return BundleArtifact(
        path=bundle_path,
        root_name=package_obj.root.name,
        file_count=len(included_files),
        sha256=build_bundle_sha256(bundle_path),
        included_files=tuple(str(path.relative_to(package_obj.root)) for path in included_files),
    )


def _bundle_file_paths(package: SkillPackage) -> Iterable[Path]:
    return package.source_files

