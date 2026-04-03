from __future__ import annotations

import sys

from .paths import PlatformPaths, detect_platform_paths


def ensure_vendor_paths() -> PlatformPaths:
    paths = detect_platform_paths()
    paths.ensure_exists()
    for entry in (paths.agent_skill_os_src, paths.autoresearch_src):
        entry_str = str(entry)
        if entry_str not in sys.path:
            sys.path.insert(0, entry_str)
    return paths
