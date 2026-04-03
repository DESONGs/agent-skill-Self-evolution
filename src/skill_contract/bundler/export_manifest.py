from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from skill_contract.bundler.contracts import (
    AdapterArtifact,
    BundleArtifact,
    ExportManifestArtifact,
    RuntimeInstallArtifact,
    SkillPackage,
)


def build_export_manifest(
    package: SkillPackage,
    output_dir: Path | str,
    source_bundle: BundleArtifact,
    target_bundles: Iterable[AdapterArtifact],
    runtime_install: RuntimeInstallArtifact | None = None,
) -> ExportManifestArtifact:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "skill-export-manifest.v1",
        "name": package.slug,
        "version": package.version,
        "source_root": str(package.root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_bundle": source_bundle.to_manifest_entry(),
        "targets": {artifact.platform: artifact.to_manifest_entry() for artifact in target_bundles},
        "portable_semantics": package.portable_semantics,
        "source_contract": {
            "manifest": package.manifest,
            "frontmatter": package.frontmatter,
        },
    }
    if runtime_install is not None:
        payload["runtime_install"] = runtime_install.to_manifest_entry()

    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ExportManifestArtifact(path=manifest_path, payload=payload)

