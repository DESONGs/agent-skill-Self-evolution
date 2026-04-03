from __future__ import annotations

from skill_contract.models import ContractValidationReport, SkillActionsDocument
from skill_contract.validators.base import error


def validate_actions(actions: SkillActionsDocument) -> ContractValidationReport:
    issues = []
    if actions.schema_version != "actions.v1":
        issues.append(error("invalid_actions_schema_version", "schema_version must be actions.v1"))

    seen: set[str] = set()
    for idx, action in enumerate(actions.actions):
        location = f"actions[{idx}]"
        if action.id in seen:
            issues.append(error("duplicate_action_id", f"Duplicate action id: {action.id}", path=location))
        seen.add(action.id)

        if action.timeout_sec <= 0:
            issues.append(error("invalid_timeout", "timeout_sec must be greater than zero", path=location))

        if action.kind == "script":
            if not action.entry:
                issues.append(error("missing_script_entry", "script actions require entry", path=location))
            if not action.runtime:
                issues.append(error("missing_script_runtime", "script actions require runtime", path=location))
        else:
            if not action.entry:
                issues.append(error("missing_action_entry", "actions require entry", path=location))

        if action.kind in {"mcp", "subagent"} and action.runtime:
            issues.append(error("unexpected_runtime", f"{action.kind} actions should not declare runtime", path=location))

    return ContractValidationReport.from_issues(issues)

