from __future__ import annotations

import math
from pathlib import Path

from skill_contract.models import ContractValidationReport, ParsedSkillPackage
from skill_contract.validators.base import error, warning

RESOURCE_DIRS = ("references", "scripts", "reports")
OPTIONAL_DIRS = ("references", "scripts", "assets", "evals", "reports")
CONTEXT_BUDGETS = {
    "scaffold": 700,
    "production": 1000,
    "library": 1300,
    "governed": 1300,
}
SKILL_BODY_WARN_RATIO = 0.85
SKILL_BODY_BUFFER = 100


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _has_files(path: Path) -> bool:
    return path.exists() and any(child.is_file() for child in path.rglob("*"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _budget_limit(package: ParsedSkillPackage) -> int:
    tier = package.manifest.context_budget_tier or package.manifest.maturity_tier
    return CONTEXT_BUDGETS.get(tier or "production", CONTEXT_BUDGETS["production"])


def _explicit_dir_reference(dirname: str, path: Path, skill_text: str, declared_components: set[str]) -> bool:
    lowered = skill_text.lower()
    if dirname.lower() in lowered or f"{dirname}/" in lowered:
        return True
    if dirname in declared_components:
        return True
    for file in path.rglob("*"):
        if file.is_file() and file.name.lower() in lowered:
            return True
    return False


def validate_resource_boundaries(package: ParsedSkillPackage) -> ContractValidationReport:
    issues = []
    root = package.root
    skill_text = package.skill_md.body
    declared_components = set(package.manifest.factory_components)

    skill_body_tokens = _estimate_tokens(skill_text)
    interface_tokens = _estimate_tokens(_read_text(root / "agents" / "interface.yaml"))
    initial_load_tokens = skill_body_tokens + interface_tokens
    budget_limit = _budget_limit(package)
    skill_body_limit = max(int(budget_limit * SKILL_BODY_WARN_RATIO), budget_limit - SKILL_BODY_BUFFER)

    if initial_load_tokens > budget_limit:
        issues.append(
            error(
                "initial_load_token_budget_exceeded",
                "Estimated initial-load tokens exceed the configured context budget",
                path=root / "SKILL.md",
                details={"estimated_tokens": initial_load_tokens, "budget_limit": budget_limit},
            )
        )
    if skill_body_tokens > skill_body_limit:
        issues.append(
            warning(
                "skill_md_too_heavy",
                "SKILL.md is too heavy relative to the initial-load budget",
                path=root / "SKILL.md",
                details={"skill_body_tokens": skill_body_tokens, "skill_body_limit": skill_body_limit},
            )
        )

    for dirname in OPTIONAL_DIRS:
        dir_path = root / dirname
        if not dir_path.exists():
            continue
        if not _has_files(dir_path):
            if dirname in RESOURCE_DIRS:
                issues.append(
                    warning(
                        "empty_resource_dir",
                        "Optional resource directory exists but does not contain files",
                        path=dir_path,
                        details={"directory": dirname},
                    )
                )
            continue
        if dirname in RESOURCE_DIRS and not _explicit_dir_reference(dirname, dir_path, skill_text, declared_components):
            issues.append(
                warning(
                    "unreferenced_resource_dir",
                    "Resource directory contains files but is not declared or referenced",
                    path=dir_path,
                    details={"directory": dirname},
                )
            )

    return ContractValidationReport.from_issues(issues)
