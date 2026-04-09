from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractValidationReport, ParsedSkillPackage
from skill_contract.validators.base import error


def _entry_within_root(root: Path, entry: str) -> tuple[bool, Path]:
    candidate = (root / entry).resolve()
    root_resolved = root.resolve()
    try:
        within = candidate.is_relative_to(root_resolved)
    except AttributeError:  # pragma: no cover - Python 3.10 safety
        within = str(candidate).startswith(str(root_resolved))
    return within, candidate


def validate_runtime_entries(package: ParsedSkillPackage, action_id: str | None = None) -> ContractValidationReport:
    issues = []
    root = package.root
    actions = package.actions.actions
    if action_id is not None:
        actions = [action for action in actions if action.id == action_id]
        if not actions:
            issues.append(error("unknown_action_id", f"Unknown action id: {action_id}"))
            return ContractValidationReport.from_issues(issues)

    for action in actions:
        if not action.entry:
            continue
        within_root, candidate = _entry_within_root(root, action.entry)
        if not within_root:
            issues.append(
                error(
                    "entry_outside_package_root",
                    "Action entry must stay inside the package root",
                    path=candidate,
                    details={"entry": action.entry},
                )
            )
            continue
        if not candidate.exists():
            issues.append(
                error(
                    "entry_not_found",
                    "Action entry does not exist",
                    path=candidate,
                    details={"entry": action.entry},
                )
            )

    return ContractValidationReport.from_issues(issues)

