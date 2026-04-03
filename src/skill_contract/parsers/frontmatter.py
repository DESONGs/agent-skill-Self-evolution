from __future__ import annotations

from typing import Any

import yaml
from pydantic import ValidationError

from skill_contract.models import (
    ContractIssue,
    ContractParseError,
    ContractSeverity,
    SkillFrontmatter,
    validation_error_to_issues,
)


def extract_frontmatter(text: str, source: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        raise ContractParseError(
            [ContractIssue(code="missing_frontmatter", message="Missing YAML frontmatter", severity=ContractSeverity.ERROR, location=source)],
            source=source,
        )

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ContractParseError(
            [ContractIssue(code="unterminated_frontmatter", message="Frontmatter block is not closed", severity=ContractSeverity.ERROR, location=source)],
            source=source,
        )

    frontmatter_text = parts[1]
    body = parts[2].lstrip("\n")
    try:
        raw = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise ContractParseError(
            [ContractIssue(code="invalid_frontmatter_yaml", message=str(exc), severity=ContractSeverity.ERROR, location=source)],
            source=source,
        ) from exc

    if not isinstance(raw, dict):
        raise ContractParseError(
            [ContractIssue(code="invalid_frontmatter_shape", message="Frontmatter must be a mapping", severity=ContractSeverity.ERROR, location=source)],
            source=source,
        )

    return raw, body


def parse_skill_frontmatter(text: str, source: str = "SKILL.md") -> SkillFrontmatter:
    raw, _ = extract_frontmatter(text, source)
    try:
        return SkillFrontmatter.model_validate(raw)
    except ValidationError as exc:
        raise ContractParseError(validation_error_to_issues(exc, source), source=source) from exc

