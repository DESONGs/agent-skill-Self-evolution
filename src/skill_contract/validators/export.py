from __future__ import annotations

import json
from pathlib import Path

from skill_contract.adapters.base import TARGET_CONTRACTS
from skill_contract.models import ContractValidationReport, ParsedSkillPackage
from skill_contract.validators.base import error


def _portable_semantics(package: ParsedSkillPackage) -> dict[str, object]:
    compatibility = package.interface.compatibility
    return {
        "activation": compatibility.activation.model_dump(),
        "execution": compatibility.execution.model_dump(),
        "trust": compatibility.trust.model_dump(),
        "degradation": dict(compatibility.degradation),
    }


def validate_export_contract(
    package: ParsedSkillPackage,
    targets_root: Path | None = None,
) -> ContractValidationReport:
    issues = []
    portable_semantics = _portable_semantics(package)
    adapter_targets = package.interface.compatibility.adapter_targets

    for target in adapter_targets:
        contract = TARGET_CONTRACTS.get(target)
        if contract is None:
            issues.append(
                error(
                    "unsupported_adapter_target",
                    "adapter target is not supported by the export contract",
                    path=package.root / "agents" / "interface.yaml",
                    details={"target": target},
                )
            )
            continue

        if targets_root is None:
            continue

        target_root = targets_root / target
        missing_files = [rel for rel in contract["required_files"] if not (target_root / rel).exists()]
        for rel in missing_files:
            issues.append(
                error(
                    "missing_export_file",
                    "Required export file is missing",
                    path=target_root / rel,
                    details={"target": target, "file": rel},
                )
            )

        adapter_json = target_root / "adapter.json"
        if not adapter_json.exists():
            continue

        payload = json.loads(adapter_json.read_text(encoding="utf-8"))
        for field in contract["required_fields"]:
            if field not in payload:
                issues.append(
                    error(
                        "missing_export_field",
                        "Required export field is missing",
                        path=adapter_json,
                        details={"target": target, "field": field},
                    )
                )

        exported_semantics = payload.get("portable_semantics")
        if exported_semantics != portable_semantics:
            issues.append(
                error(
                    "portable_semantics_mismatch",
                    "Exported portable semantics must exactly match the neutral source",
                    path=adapter_json,
                    details={"target": target},
                )
            )

    return ContractValidationReport.from_issues(issues)
