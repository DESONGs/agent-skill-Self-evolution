from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlatformPaths:
    platform_root: Path
    docs_root: Path
    engineering_docs_root: Path
    vendor_root: Path
    agent_skill_os_src: Path
    autoresearch_src: Path

    def ensure_exists(self) -> None:
        required = (
            self.platform_root,
            self.docs_root,
            self.engineering_docs_root,
            self.vendor_root,
            self.agent_skill_os_src,
            self.autoresearch_src,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing merged platform paths: {missing}")

    def to_dict(self) -> dict[str, str]:
        return {
            "platform_root": str(self.platform_root),
            "docs_root": str(self.docs_root),
            "engineering_docs_root": str(self.engineering_docs_root),
            "vendor_root": str(self.vendor_root),
            "agent_skill_os_src": str(self.agent_skill_os_src),
            "autoresearch_src": str(self.autoresearch_src),
        }


def detect_platform_paths() -> PlatformPaths:
    platform_root = Path(__file__).resolve().parents[2]
    docs_root = platform_root / "docs"
    vendor_root = platform_root / "vendor"
    return PlatformPaths(
        platform_root=platform_root,
        docs_root=docs_root,
        engineering_docs_root=docs_root / "engineering",
        vendor_root=vendor_root,
        agent_skill_os_src=vendor_root / "agentskillos" / "src",
        autoresearch_src=vendor_root / "autoresearch" / "src",
    )
