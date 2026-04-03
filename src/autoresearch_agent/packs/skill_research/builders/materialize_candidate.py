from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from autoresearch_agent.core.packs.loader import load_document


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = PACKAGE_ROOT / "templates"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_candidate(candidate: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return candidate
    return load_document(Path(candidate))


def _render(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("${" + key + "}", value)
    return rendered


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    safe = text and all(ch.isalnum() or ch in {"-", "_", ".", "/", ":"} for ch in text)
    return text if safe else json.dumps(text, ensure_ascii=False)


def _render_actions(actions_payload: dict[str, Any]) -> str:
    lines = ["schema_version: actions.v1", "actions:"]
    items = actions_payload.get("items", []) if isinstance(actions_payload, dict) else []
    if not items:
        lines.append("  []")
        return "\n".join(lines) + "\n"
    for action in items:
        if not isinstance(action, dict):
            continue
        lines.extend(
            [
                f"  - id: {_yaml_scalar(action.get('id', 'run'))}",
                f"    kind: {_yaml_scalar(action.get('kind', 'script'))}",
                f"    entry: {_yaml_scalar(action.get('entry', 'scripts/run.py'))}",
                f"    runtime: {_yaml_scalar(action.get('runtime', 'python3'))}",
                f"    timeout_sec: {_yaml_scalar(action.get('timeout_sec', 120))}",
                f"    sandbox: {_yaml_scalar(action.get('sandbox', 'workspace-write'))}",
            ]
        )
    return "\n".join(lines) + "\n"


def materialize_candidate(candidate: dict[str, Any] | str | Path, output_dir: str | Path) -> dict[str, Any]:
    payload = _load_candidate(candidate)
    candidate_info = payload.get("candidate", {})
    skill_info = payload.get("skill", {})
    governance = payload.get("governance", {})
    boundary = skill_info.get("boundary", {})

    values = {
        "CANDIDATE_ID": str(candidate_info.get("id", "")),
        "CANDIDATE_SLUG": str(candidate_info.get("slug", "")),
        "CANDIDATE_TITLE": str(candidate_info.get("title", skill_info.get("name", ""))),
        "SOURCE_KIND": str(candidate_info.get("source_kind", "")),
        "CREATED_AT": str(candidate_info.get("created_at", "")),
        "TARGET_USER": str(payload.get("qualification", {}).get("target_user", "")),
        "PROBLEM_STATEMENT": str(payload.get("qualification", {}).get("problem_statement", "")),
        "SKILL_NAME": str(skill_info.get("name", "")),
        "SKILL_DESCRIPTION": str(skill_info.get("description", "")),
        "TRIGGER_DESCRIPTION": str(skill_info.get("trigger_description", "")),
        "DEFAULT_ACTION": str(payload.get("actions", {}).get("default_action", "")),
        "OWNER": str(governance.get("owner", "")),
        "UPDATED_AT": str(payload.get("candidate", {}).get("created_at", "")),
        "SHORT_DESCRIPTION": str(skill_info.get("description", "")),
        "DEFAULT_PROMPT": f"Use {skill_info.get('name', '')} to handle the skill_research workflow.",
        "BOUNDS_OWNS": ", ".join(boundary.get("owns", []) or []),
        "BOUNDS_NOT_OWNS": ", ".join(boundary.get("does_not_own", []) or []),
        "OUTPUT_CONTRACT": ", ".join((skill_info.get("workflow", {}) or {}).get("outputs", []) or []),
        "RECURRING_JOB": str(payload.get("sources", {}).get("normalized_summary", {}).get("recurring_job", "")),
    }

    output_root = Path(output_dir)
    generated_root = output_root / "generated"
    generated_root.mkdir(parents=True, exist_ok=True)

    skill_dir = generated_root / str(candidate_info.get("slug", "candidate") or "candidate")
    (skill_dir / "agents").mkdir(parents=True, exist_ok=True)
    for dirname in ("references", "scripts", "evals", "reports"):
        (skill_dir / dirname).mkdir(parents=True, exist_ok=True)

    files = {
        "research.yaml": _render(_load_text(TEMPLATES_ROOT / "research.yaml"), values),
        "SKILL.md": _render(_load_text(TEMPLATES_ROOT / "SKILL.md.j2"), values),
        "manifest.json": _render(_load_text(TEMPLATES_ROOT / "manifest.json.j2"), values),
        "actions.yaml": _render_actions(payload.get("actions", {})),
        "agents/interface.yaml": _render(_load_text(TEMPLATES_ROOT / "interface.yaml.j2"), values),
        "candidate.yaml": Path(candidate).read_text(encoding="utf-8") if not isinstance(candidate, dict) else json.dumps(payload, ensure_ascii=False, indent=2),
        "references/README.md": "# References\n\nMaterialized references for this candidate.\n",
        "evals/README.md": "# Evals\n\nTrigger, boundary, and safety cases live here.\n",
        "reports/README.md": "# Reports\n\nGenerated gate evidence lives here.\n",
    }
    for action in payload.get("actions", {}).get("items", []) or []:
        if not isinstance(action, dict):
            continue
        entry = str(action.get("entry", "")).strip()
        if not entry:
            continue
        files.setdefault(
            entry,
            "\n".join(
                [
                    "from __future__ import annotations",
                    "",
                    "def main() -> None:",
                    "    print('skill_research placeholder action')",
                    "",
                    "",
                    "if __name__ == '__main__':",
                    "    main()",
                    "",
                ]
            ),
        )
    for relative, text in files.items():
        path = skill_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    (output_root / "research.yaml").write_text(files["research.yaml"], encoding="utf-8")

    return {
        "ok": True,
        "candidate_id": values["CANDIDATE_ID"],
        "candidate_slug": values["CANDIDATE_SLUG"],
        "generated_dir": str(skill_dir),
        "files": [str((output_root / "research.yaml").relative_to(output_root))] + [
            str((skill_dir / relative).relative_to(output_root)) for relative in files if relative != "research.yaml"
        ],
    }
