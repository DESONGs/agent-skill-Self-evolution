from __future__ import annotations

from pathlib import Path

from skill_contract.adapters.base import build_openai_adapter
from skill_contract.bundler.contracts import AdapterArtifact, SkillPackage


def build_adapter(package: SkillPackage, target_root: Path) -> AdapterArtifact:
    return build_openai_adapter(package, target_root)

