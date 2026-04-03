from __future__ import annotations

from .paths import PlatformPaths, detect_platform_paths


def ensure_source_layout() -> PlatformPaths:
    paths = detect_platform_paths()
    paths.ensure_exists()
    return paths
