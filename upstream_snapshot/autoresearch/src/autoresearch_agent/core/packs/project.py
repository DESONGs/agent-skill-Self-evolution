from __future__ import annotations

from pathlib import Path
from typing import Any
import re
from datetime import date

from .loader import dump_document, find_pack_manifest, resolve_pack_file
from .schema import ResearchSpec, build_default_research_spec
from autoresearch_agent.core.spec.research_config import dump_research_yaml


DEFAULT_PROJECT_DIRS = [
    "datasets",
    "workspace",
    "artifacts",
    ".autoresearch/runs",
    ".autoresearch/cache",
    ".autoresearch/state",
]

SKILL_RESEARCH_EXTRA_DIRS = [
    "datasets/trigger/train",
    "datasets/trigger/dev",
    "datasets/trigger/holdout",
    "datasets/boundary",
    "datasets/action",
    "datasets/safety",
    "datasets/baselines",
    "workspace/generated",
    "workspace/baselines",
    "workspace/submissions",
    "workspace/sources",
    "packs/skill_research",
]


def default_research_spec(
    *,
    project_name: str,
    pack_id: str,
    data_source: str,
    allowed_axes: list[str] | None = None,
    pack_config: dict[str, Any] | None = None,
) -> ResearchSpec:
    return build_default_research_spec(
        project_name=project_name,
        pack_id=pack_id,
        data_source=data_source,
        allowed_axes=allowed_axes,
        pack_config=pack_config,
    )


def render_research_spec(spec: ResearchSpec) -> str:
    return dump_research_yaml(spec.to_dict())


def render_pack_template(path: Path, placeholders: dict[str, str] | None = None) -> str:
    template = path.read_text(encoding="utf-8")
    if not placeholders:
        return template
    for key, value in placeholders.items():
        template = template.replace("${" + key + "}", value)
    return template


def _pack_scaffold_dirs(pack_id: str) -> list[str]:
    if pack_id == "skill_research":
        return SKILL_RESEARCH_EXTRA_DIRS
    return []


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(text or "").strip().lower())
    return value.strip("-") or "candidate"


def _template_placeholders(*, project_name: str, pack_id: str, data_source: str) -> dict[str, str]:
    slug = _slugify(project_name)
    return {
        "PROJECT_NAME": project_name,
        "PACK_ID": pack_id,
        "DATA_SOURCE": data_source,
        "CANDIDATE_ID": f"cand_{slug}_001",
        "CANDIDATE_SLUG": slug,
        "CANDIDATE_TITLE": project_name,
        "SOURCE_KIND": "workflow",
        "CREATED_AT": date.today().isoformat(),
        "TARGET_USER": "platform-agent-team",
        "PROBLEM_STATEMENT": f"{project_name} should be packaged as a reusable skill candidate.",
        "SKILL_NAME": project_name,
        "SKILL_DESCRIPTION": f"Reusable skill package scaffold for {project_name}.",
        "TRIGGER_DESCRIPTION": f"Use when asked to work on {project_name.lower()} skill packaging, evaluation, or promotion.",
        "DEFAULT_ACTION": "materialize_package",
        "OWNER": "platform-agent-team",
        "UPDATED_AT": date.today().isoformat(),
        "SHORT_DESCRIPTION": f"Reusable skill package scaffold for {project_name}.",
        "DEFAULT_PROMPT": f"Use {project_name} to handle skill factory and skill lab workflows.",
        "BOUNDS_OWNS": "skill packaging, trigger routing, eval bundle generation",
        "BOUNDS_NOT_OWNS": "runtime execution internals, registry schema internals",
        "OUTPUT_CONTRACT": "generated package, gate summary, submission bundle",
        "RECURRING_JOB": f"Support {project_name} as a reusable skill package",
    }


def _ensure_data_placeholder(project_root: Path, data_source: str) -> None:
    target = Path(data_source)
    target = target if target.is_absolute() else (project_root / target)
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("[]\n", encoding="utf-8")


def create_project_scaffold(
    project_root: Path,
    *,
    project_name: str,
    pack_id: str,
    data_source: str = "./datasets/eval_markets.json",
    pack_config: dict[str, Any] | None = None,
) -> dict[str, Path]:
    pack_manifest = find_pack_manifest(pack_id)
    project_root = project_root.resolve()
    created_paths: dict[str, Path] = {}

    for relative_dir in DEFAULT_PROJECT_DIRS:
        path = project_root / relative_dir
        path.mkdir(parents=True, exist_ok=True)
        created_paths[relative_dir] = path
    for relative_dir in _pack_scaffold_dirs(pack_manifest.pack_id):
        path = project_root / relative_dir
        path.mkdir(parents=True, exist_ok=True)
        created_paths[relative_dir] = path

    research_path = project_root / "research.yaml"
    research_template = str(pack_manifest.entrypoints.get("research_template", "") or "").strip()
    editable_target = pack_manifest.editable_targets[0] if pack_manifest.editable_targets else "workspace/strategy.py"
    if research_template:
        placeholders = _template_placeholders(project_name=project_name, pack_id=pack_manifest.pack_id, data_source=data_source)
        placeholders["EDITABLE_TARGET"] = editable_target
        rendered = render_pack_template(
            resolve_pack_file(pack_manifest, research_template),
            placeholders,
        )
        research_path.write_text(rendered, encoding="utf-8")
    else:
        spec = default_research_spec(
            project_name=project_name,
            pack_id=pack_manifest.pack_id,
            data_source=data_source,
            allowed_axes=pack_manifest.allowed_axes,
            pack_config=pack_config,
        )
        spec = ResearchSpec(
            schema_version=spec.schema_version,
            project=spec.project,
            pack=spec.pack,
            data=spec.data,
            objective=spec.objective,
            search={**spec.search, "editable_targets": [editable_target]},
            evaluation=spec.evaluation,
            constraints=spec.constraints,
            runtime=spec.runtime,
            outputs=spec.outputs,
            pack_config=spec.pack_config,
        )
        research_path.write_text(render_research_spec(spec), encoding="utf-8")
    created_paths["research.yaml"] = research_path

    template_path = project_root / editable_target
    editable_template = str(pack_manifest.entrypoints.get("strategy_template", "") or "").strip()
    if not editable_template:
        editable_template = str(pack_manifest.entrypoints.get("candidate_template", "") or "").strip()
    if editable_template:
        placeholders = _template_placeholders(project_name=project_name, pack_id=pack_manifest.pack_id, data_source=data_source)
        rendered = render_pack_template(
            resolve_pack_file(pack_manifest, editable_template),
            placeholders,
        )
        template_path.write_text(rendered, encoding="utf-8")
    else:
        template_path.write_text("# editable template\n", encoding="utf-8")
    created_paths[editable_target] = template_path

    manifest_copy_path = project_root / ".autoresearch" / "state" / "pack_manifest.json"
    manifest_copy_path.write_text(dump_document(pack_manifest.to_dict()), encoding="utf-8")
    created_paths[".autoresearch/state/pack_manifest.json"] = manifest_copy_path

    dataset_readme = project_root / "datasets" / "README.md"
    if not dataset_readme.exists():
        dataset_readme.write_text(
            "Put your dataset files here and point `data.source` at the chosen file.\n",
            encoding="utf-8",
        )
    created_paths["datasets/README.md"] = dataset_readme
    if pack_manifest.pack_id == "skill_research":
        _ensure_data_placeholder(project_root, data_source)
    return created_paths
