from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_boundary_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    skill_md = package_root / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
    report = {
        "ok": skill_md.exists(),
        "package_dir": str(package_root),
        "boundary_markers": {
            "owns": "Owns:" in text or "owns:" in text,
            "does_not_own": "Does not own:" in text or "does not own:" in text,
        },
    }
    return report


def write_boundary_report(package_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = evaluate_boundary_package(package_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

