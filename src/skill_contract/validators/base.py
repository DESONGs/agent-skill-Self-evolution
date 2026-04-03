from __future__ import annotations

from pathlib import Path

from skill_contract.models import ContractIssue, ContractSeverity, ContractValidationReport, path_issue


def error(code: str, message: str, *, path: Path | str | None = None, details: dict | None = None) -> ContractIssue:
    return path_issue(code, message, path=path, details=details, severity=ContractSeverity.ERROR)


def warning(code: str, message: str, *, path: Path | str | None = None, details: dict | None = None) -> ContractIssue:
    return path_issue(code, message, path=path, details=details, severity=ContractSeverity.WARNING)


def ok_report() -> ContractValidationReport:
    return ContractValidationReport(ok=True, issues=[])

