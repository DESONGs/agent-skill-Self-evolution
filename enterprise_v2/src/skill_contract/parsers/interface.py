from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from skill_contract.models import ContractIssue, ContractParseError, ContractSeverity, SkillInterfaceDocument, validation_error_to_issues


def parse_interface(path: Path) -> SkillInterfaceDocument:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ContractParseError(
            [ContractIssue(code="invalid_interface_yaml", message=str(exc), severity=ContractSeverity.ERROR, location=str(path))],
            source=str(path),
        ) from exc

    if not isinstance(raw, dict):
        raise ContractParseError(
            [ContractIssue(code="invalid_interface_shape", message="interface.yaml must be a mapping", severity=ContractSeverity.ERROR, location=str(path))],
            source=str(path),
        )

    try:
        return SkillInterfaceDocument.model_validate(raw)
    except ValidationError as exc:
        raise ContractParseError(validation_error_to_issues(exc, str(path)), source=str(path)) from exc

