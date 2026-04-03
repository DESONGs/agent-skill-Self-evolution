from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractValidationReport, SkillManifest, SkillMdDocument
from skill_contract.validators.base import error


def validate_manifest(manifest: SkillManifest, skill_md: SkillMdDocument, manifest_path: Path) -> ContractValidationReport:
    issues = []
    if manifest.name != skill_md.frontmatter.name:
        issues.append(
            error(
                "manifest_name_mismatch",
                "manifest.json name must match SKILL.md frontmatter.name",
                path=manifest_path,
                details={"manifest_name": manifest.name, "skill_name": skill_md.frontmatter.name},
            )
        )

    if manifest.deprecation_note is None and manifest.status == "deprecated":
        issues.append(
            error(
                "missing_deprecation_note",
                "deprecated manifests should include deprecation_note",
            )
        )

    return ContractValidationReport.from_issues(issues)
