from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from skill_contract.models import ContractParseError, SkillFrontmatter, SkillMdDocument, validation_error_to_issues
from skill_contract.parsers.frontmatter import extract_frontmatter


def parse_skill_md(path: Path) -> SkillMdDocument:
    text = path.read_text(encoding="utf-8")
    raw_frontmatter, body = extract_frontmatter(text, str(path))
    try:
        parsed_frontmatter = SkillFrontmatter.model_validate(raw_frontmatter)
        return SkillMdDocument(path=path, frontmatter=parsed_frontmatter, body=body)
    except ValidationError as exc:
        raise ContractParseError(validation_error_to_issues(exc, str(path)), source=str(path)) from exc
