from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def evaluate_trigger_package(package_dir: str | Path, eval_dir: str | Path | None = None) -> dict[str, Any]:
    package_root = Path(package_dir)
    skill_md = package_root / "SKILL.md"
    manifest = package_root / "manifest.json"
    trigger_text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
    report = {
        "ok": skill_md.exists() and manifest.exists(),
        "package_dir": str(package_root),
        "signal": {
            "has_trigger_description": "description:" in trigger_text or "Trigger" in trigger_text,
            "has_boundary": "Boundary" in trigger_text,
        },
        "paths": {
            "eval_dir": str(eval_dir) if eval_dir is not None else "",
        },
    }
    return report


def write_trigger_report(package_dir: str | Path, output_path: str | Path, eval_dir: str | Path | None = None) -> dict[str, Any]:
    report = evaluate_trigger_package(package_dir, eval_dir=eval_dir)
    Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

