from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from skill_contract.models import ContractIssue, ContractParseError, ContractSeverity, SkillActionsDocument, validation_error_to_issues


def load_actions_mapping(source: str | dict[str, Any] | Path) -> dict[str, Any]:
    path_hint = source if isinstance(source, Path) else None
    try:
        if isinstance(source, dict):
            raw = source
        else:
            text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
            raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ContractParseError(
            [ContractIssue(code="invalid_actions_yaml", message=str(exc), severity=ContractSeverity.ERROR, location=str(path_hint) if path_hint else "actions.yaml")],
            source=str(path_hint) if path_hint else "actions.yaml",
        ) from exc

    if not isinstance(raw, dict):
        location = str(path_hint) if path_hint else "actions.yaml"
        raise ContractParseError(
            [ContractIssue(code="invalid_actions_shape", message="actions.yaml must be a mapping", severity=ContractSeverity.ERROR, location=location)],
            source=location,
        )
    return raw


def parse_actions_source(source: str | dict[str, Any] | Path) -> SkillActionsDocument:
    path_hint = source if isinstance(source, Path) else None
    raw = load_actions_mapping(source)
    location = str(path_hint) if path_hint else "actions.yaml"
    try:
        return SkillActionsDocument.model_validate(raw)
    except ValidationError as exc:
        raise ContractParseError(validation_error_to_issues(exc, location), source=location) from exc


def parse_actions(path: Path) -> SkillActionsDocument:
    try:
        return parse_actions_source(path)
    except ContractParseError:
        raise
