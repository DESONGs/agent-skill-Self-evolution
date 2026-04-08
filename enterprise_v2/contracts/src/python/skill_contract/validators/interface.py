from __future__ import annotations

from skill_contract.models import ContractValidationReport, SkillInterfaceDocument
from skill_contract.validators.base import error


def validate_interface(interface: SkillInterfaceDocument) -> ContractValidationReport:
    issues = []
    compat = interface.compatibility

    if compat.canonical_format != "agent-skills":
        issues.append(error("invalid_canonical_format", "canonical_format must be agent-skills"))
    if not compat.adapter_targets:
        issues.append(error("missing_adapter_targets", "adapter_targets must not be empty"))

    missing_targets = [target for target in compat.adapter_targets if target not in compat.degradation]
    if missing_targets:
        issues.append(
            error(
                "missing_degradation_entries",
                "degradation must cover every adapter target",
                details={"missing_targets": missing_targets},
            )
        )

    if compat.activation.mode == "path_scoped" and not compat.activation.paths:
        issues.append(error("missing_activation_paths", "path_scoped activation requires paths"))

    return ContractValidationReport.from_issues(issues)

