from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_governance_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    manifest = package_root / "manifest.json"
    skill_md = package_root / "SKILL.md"
    report = {
        "ok": manifest.exists() and skill_md.exists(),
        "package_dir": str(package_root),
        "manifest_present": manifest.exists(),
        "skill_present": skill_md.exists(),
    }
    return report


def write_governance_report(package_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = evaluate_governance_package(package_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

