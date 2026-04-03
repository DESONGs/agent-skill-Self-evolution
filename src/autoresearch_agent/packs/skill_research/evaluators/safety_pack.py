from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_safety_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    scripts_dir = package_root / "scripts"
    report = {
        "ok": package_root.exists(),
        "package_dir": str(package_root),
        "scripts_present": scripts_dir.exists(),
        "network_allowed": False,
    }
    return report


def write_safety_report(package_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = evaluate_safety_package(package_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

