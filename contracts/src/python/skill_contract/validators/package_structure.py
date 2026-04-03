from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractValidationReport
from skill_contract.validators.base import error


REQUIRED_FILES = (
    "SKILL.md",
    "manifest.json",
    "actions.yaml",
    "agents/interface.yaml",
)


def validate_package_structure(root: Path) -> ContractValidationReport:
    issues = []
    if not root.exists():
        issues.append(error("missing_package_root", "Skill package root does not exist", path=root))
        return ContractValidationReport.from_issues(issues)

    if not root.is_dir():
        issues.append(error("package_root_not_directory", "Skill package root must be a directory", path=root))
        return ContractValidationReport.from_issues(issues)

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            issues.append(error("missing_required_file", f"Missing required file: {rel}", path=root / rel))

    agents_dir = root / "agents"
    if agents_dir.exists() and not agents_dir.is_dir():
        issues.append(error("agents_not_directory", "agents must be a directory", path=agents_dir))

    return ContractValidationReport.from_issues(issues)

