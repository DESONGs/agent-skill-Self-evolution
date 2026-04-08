from __future__ import annotations

import sys

from .paths import PlatformPaths, detect_platform_paths


def ensure_source_layout() -> PlatformPaths:
    paths = detect_platform_paths()
    paths.ensure_exists()
    for source_root in reversed(paths.python_source_roots()):
        source_text = str(source_root)
        if source_text not in sys.path:
            sys.path.insert(0, source_text)
    return paths
