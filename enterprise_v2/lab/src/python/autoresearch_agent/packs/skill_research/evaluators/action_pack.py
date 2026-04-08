from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_action_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    actions = package_root / "actions.yaml"
    scripts_dir = package_root / "scripts"
    report = {
        "ok": actions.exists(),
        "package_dir": str(package_root),
        "actions_present": actions.exists(),
        "scripts_present": scripts_dir.exists(),
    }
    return report


def write_action_report(package_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = evaluate_action_package(package_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

