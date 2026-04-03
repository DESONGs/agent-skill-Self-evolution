from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractParseError, ContractValidationReport
from skill_contract.parsers.package import load_skill_package
from skill_contract.validators.actions import validate_actions
from skill_contract.validators.export import validate_export_contract
from skill_contract.validators.governance import validate_governance
from skill_contract.validators.interface import validate_interface
from skill_contract.validators.manifest import validate_manifest
from skill_contract.validators.package_structure import validate_package_structure
from skill_contract.validators.resource_boundary import validate_resource_boundaries
from skill_contract.validators.runtime_entry import validate_runtime_entries
from skill_contract.validators.skill_md import validate_skill_md


def validate_skill_package(root: Path, action_id: str | None = None) -> ContractValidationReport:
    structure = validate_package_structure(root)
    if not structure.ok:
        return structure

    try:
        package = load_skill_package(root)
    except ContractParseError as exc:
        return ContractValidationReport.from_issues(exc.issues)

    report = structure
    report = report.merged(validate_skill_md(package.skill_md, root))
    report = report.merged(validate_manifest(package.manifest, package.skill_md, root / "manifest.json"))
    report = report.merged(validate_actions(package.actions))
    report = report.merged(validate_interface(package.interface))
    report = report.merged(validate_governance(package))
    report = report.merged(validate_resource_boundaries(package))
    report = report.merged(validate_export_contract(package))
    report = report.merged(validate_runtime_entries(package, action_id=action_id))
    return report
