from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlatformPaths:
    platform_root: Path
    source_root: Path
    contracts_root: Path
    runtime_root: Path
    registry_root_dir: Path
    lab_root: Path
    factory_root: Path
    docs_root: Path
    engineering_docs_root: Path
    data_root: Path
    upstream_snapshot_root: Path

    def ensure_exists(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        required = (
            self.platform_root,
            self.source_root,
            self.contracts_root,
            self.runtime_root,
            self.registry_root_dir,
            self.lab_root,
            self.factory_root,
            self.docs_root,
            self.engineering_docs_root,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing merged platform paths: {missing}")

    def python_source_roots(self) -> tuple[Path, ...]:
        return (
            self.source_root,
            self.contracts_root / "src" / "python",
            self.runtime_root / "src" / "python",
            self.lab_root / "src" / "python",
            self.factory_root / "src" / "python",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "platform_root": str(self.platform_root),
            "source_root": str(self.source_root),
            "contracts_root": str(self.contracts_root),
            "runtime_root": str(self.runtime_root),
            "registry_root": str(self.registry_root_dir),
            "lab_root": str(self.lab_root),
            "factory_root": str(self.factory_root),
            "docs_root": str(self.docs_root),
            "engineering_docs_root": str(self.engineering_docs_root),
            "data_root": str(self.data_root),
            "upstream_snapshot_root": str(self.upstream_snapshot_root),
        }


def detect_platform_paths() -> PlatformPaths:
    platform_root = Path(__file__).resolve().parents[2]
    source_root = platform_root / "src"
    contracts_root = platform_root / "contracts"
    runtime_root = platform_root / "runtime"
    registry_root_dir = platform_root / "registry"
    lab_root = platform_root / "lab"
    factory_root = platform_root / "factory"
    docs_root = platform_root / "docs"
    data_root = platform_root / ".data"
    upstream_snapshot_root = platform_root / "upstream_snapshot"
    return PlatformPaths(
        platform_root=platform_root,
        source_root=source_root,
        contracts_root=contracts_root,
        runtime_root=runtime_root,
        registry_root_dir=registry_root_dir,
        lab_root=lab_root,
        factory_root=factory_root,
        docs_root=docs_root,
        engineering_docs_root=docs_root / "engineering",
        data_root=data_root,
        upstream_snapshot_root=upstream_snapshot_root,
    )
