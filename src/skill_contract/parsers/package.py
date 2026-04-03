from __future__ import annotations

from pathlib import Path

from skill_contract.models import ParsedSkillPackage
from skill_contract.parsers.actions import parse_actions
from skill_contract.parsers.interface import parse_interface
from skill_contract.parsers.manifest import parse_manifest
from skill_contract.parsers.skill_md import parse_skill_md


def load_skill_package(root: Path) -> ParsedSkillPackage:
    return ParsedSkillPackage(
        root=root,
        skill_md=parse_skill_md(root / "SKILL.md"),
        manifest=parse_manifest(root / "manifest.json"),
        actions=parse_actions(root / "actions.yaml"),
        interface=parse_interface(root / "agents" / "interface.yaml"),
    )

