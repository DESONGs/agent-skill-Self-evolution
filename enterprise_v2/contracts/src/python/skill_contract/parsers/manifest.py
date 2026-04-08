from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from skill_contract.models import ContractIssue, ContractParseError, ContractSeverity, SkillManifest, validation_error_to_issues


def parse_manifest(path: Path) -> SkillManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractParseError(
            [
                ContractIssue(
                    code="invalid_manifest_json",
                    message=str(exc),
                    severity=ContractSeverity.ERROR,
                    location=str(path),
                    details={"path": str(path)},
                )
            ],
            source=str(path),
        ) from exc

    if not isinstance(raw, dict):
        raise ContractParseError(
            [
                ContractIssue(
                    code="invalid_manifest_shape",
                    message="Manifest must be a JSON object",
                    severity=ContractSeverity.ERROR,
                    location=str(path),
                    details={"path": str(path), "input_type": type(raw).__name__},
                )
            ],
            source=str(path),
        )

    try:
        return SkillManifest.model_validate(raw)
    except ValidationError as exc:
        raise ContractParseError(validation_error_to_issues(exc, str(path)), source=str(path)) from exc
