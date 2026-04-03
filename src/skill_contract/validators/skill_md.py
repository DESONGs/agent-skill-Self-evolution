from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractValidationReport, SkillMdDocument
from skill_contract.validators.base import error


def validate_skill_md(document: SkillMdDocument, root: Path) -> ContractValidationReport:
    issues = []
    if not document.frontmatter.name:
        issues.append(error("missing_skill_name", "SKILL.md frontmatter.name is required", path=document.path))
    if not document.frontmatter.description:
        issues.append(error("missing_skill_description", "SKILL.md frontmatter.description is required", path=document.path))

    expected_name = root.name
    if expected_name and document.frontmatter.name != expected_name:
        issues.append(
            error(
                "skill_name_root_mismatch",
                "SKILL.md name must match the package root directory name",
                path=document.path,
                details={"expected": expected_name, "actual": document.frontmatter.name},
            )
        )

    return ContractValidationReport.from_issues(issues)

