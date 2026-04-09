"""Skill loader - Parse and discover skills from skill package contracts."""

from pathlib import Path
from typing import Optional

from loguru import logger as _logger

from orchestrator.runtime.models import SkillMetadata, load_skill_package_metadata


def load_skill(skill_path: Path, max_content_chars: int = 5000) -> Optional[SkillMetadata]:
    """Load metadata from a single skill directory."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None

    try:
        return load_skill_package_metadata(skill_path, max_content_chars=max_content_chars)
    except Exception as e:
        _logger.warning(f"Failed to load skill metadata from {skill_path}: {e}")
        return None


def load_skill_content(skill_path: Path, max_chars: int = 4000) -> str:
    """Load full SKILL.md content (truncated for context management)."""
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        return content[:max_chars]
    return f"Skill not found at {skill_path}"


class SkillRegistry:
    """Registry of available skills."""

    def __init__(self, skill_dir: str = ".claude/skills"):
        self.skill_dir = Path(skill_dir)
        self._cache: dict[str, SkillMetadata] = {}

    def list_all(self) -> list[SkillMetadata]:
        """List all available skills."""
        if not self._cache:
            self._build_cache()
        return list({id(s): s for s in self._cache.values()}.values())

    def get(self, name: str) -> Optional[SkillMetadata]:
        """Get a skill by name."""
        if not self._cache:
            self._build_cache()
        return self._cache.get(name)

    def find_by_names(self, names: list[str]) -> list[SkillMetadata]:
        """Find skills by name list."""
        return [s for name in names if (s := self.get(name))]

    def get_missing(self, names: list[str]) -> list[str]:
        """Get list of skill names that were not found."""
        return [n for n in names if self.get(n) is None]

    def refresh(self) -> None:
        """Clear cache and rebuild."""
        self._cache.clear()
        self._build_cache()

    def _build_cache(self) -> None:
        """Build the skill cache by scanning the skill directory."""
        if not self.skill_dir.is_dir():
            return
        for item in self.skill_dir.iterdir():
            if item.is_dir():
                if skill := load_skill(item):
                    self._cache[skill.name] = skill
                    if skill.slug and skill.slug != skill.name:
                        self._cache[skill.slug] = skill
                    # Also index by directory name (skill ID) for lookup compatibility
                    dir_name = item.name
                    if dir_name != skill.name:
                        self._cache[dir_name] = skill

    def __len__(self) -> int:
        if not self._cache:
            self._build_cache()
        return len(self._cache)

    def __contains__(self, name: str) -> bool:
        return self.get(name) is not None
