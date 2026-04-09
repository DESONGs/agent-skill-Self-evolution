from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_resource_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    report = {
        "ok": package_root.exists(),
        "package_dir": str(package_root),
        "directory_count": sum(1 for path in package_root.rglob("*") if path.is_dir()) if package_root.exists() else 0,
        "file_count": sum(1 for path in package_root.rglob("*") if path.is_file()) if package_root.exists() else 0,
    }
    return report


def write_resource_report(package_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = evaluate_resource_package(package_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

