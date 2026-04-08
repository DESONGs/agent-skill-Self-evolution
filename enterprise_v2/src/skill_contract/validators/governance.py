from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractValidationReport, ParsedSkillPackage
from skill_contract.validators.base import error, warning

ALLOWED_MATURITY = {"scaffold", "production", "library", "governed"}
ALLOWED_REVIEW_CADENCE = {"monthly", "quarterly", "semiannual", "annual", "per-release"}
DECLARED_MATURITY_MIN_SCORE = {
    "scaffold": 0,
    "production": 80,
    "library": 85,
    "governed": 90,
}


def _has_files(path: Path) -> bool:
    return path.exists() and any(child.is_file() for child in path.rglob("*"))


def _compute_evidence_score(package: ParsedSkillPackage) -> int:
    root = package.root
    score = 0
    if package.manifest.owner:
        score += 15
    if package.manifest.review_cadence in ALLOWED_REVIEW_CADENCE:
        score += 15
    if package.manifest.maturity_tier in ALLOWED_MATURITY:
        score += 10
    if package.skill_md.frontmatter.description:
        score += 5
    if "do not use" in package.skill_md.body.lower():
        score += 5
    if (root / "agents" / "interface.yaml").exists():
        score += 10
    if _has_files(root / "references"):
        score += 10
    if _has_files(root / "scripts"):
        score += 10
    if _has_files(root / "evals"):
        score += 10
    if package.manifest.factory_components:
        score += 10
    if _has_files(root / "reports"):
        score += 5
    if _has_files(root / "assets"):
        score += 5
    return score


def validate_governance(package: ParsedSkillPackage) -> ContractValidationReport:
    issues = []
    manifest = package.manifest
    root = package.root

    if not manifest.owner:
        issues.append(error("missing_manifest_owner", "manifest.json.owner is required", path=root / "manifest.json"))
    if manifest.review_cadence not in ALLOWED_REVIEW_CADENCE:
        issues.append(
            error(
                "invalid_review_cadence",
                "manifest.json.review_cadence must be a supported cadence",
                path=root / "manifest.json",
                details={"review_cadence": manifest.review_cadence},
            )
        )
    if manifest.maturity_tier not in ALLOWED_MATURITY:
        issues.append(
            error(
                "invalid_maturity_tier",
                "manifest.json.maturity_tier must be a supported tier",
                path=root / "manifest.json",
                details={"maturity_tier": manifest.maturity_tier},
            )
        )

    for component in manifest.factory_components:
        component_path = root / component
        if not component_path.exists():
            issues.append(
                error(
                    "missing_declared_evidence_dir",
                    "Declared factory component directory is missing",
                    path=component_path,
                    details={"component": component},
                )
            )
            continue
        if not _has_files(component_path):
            issues.append(
                error(
                    "empty_declared_evidence_dir",
                    "Declared factory component directory must contain files",
                    path=component_path,
                    details={"component": component},
                )
            )

    score = _compute_evidence_score(package)
    minimum = DECLARED_MATURITY_MIN_SCORE.get(manifest.maturity_tier)
    if minimum is not None and score < minimum:
        issues.append(
            warning(
                "maturity_evidence_mismatch",
                "Declared maturity tier exceeds the available evidence score",
                path=root / "manifest.json",
                details={
                    "maturity_tier": manifest.maturity_tier,
                    "evidence_score": score,
                    "required_minimum": minimum,
                },
            )
        )

    return ContractValidationReport.from_issues(issues)
