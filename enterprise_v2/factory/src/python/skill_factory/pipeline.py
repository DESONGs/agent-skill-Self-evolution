from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch_agent.cli.runtime import init_project
from autoresearch_agent.core.skill_lab import pipeline as skill_lab_pipeline
from autoresearch_agent.packs.skill_research.builders.materialize_candidate import materialize_candidate
from autoresearch_agent.packs.skill_research.evaluators.action_pack import evaluate_action_package
from autoresearch_agent.packs.skill_research.evaluators.boundary_pack import evaluate_boundary_package
from autoresearch_agent.packs.skill_research.evaluators.governance_pack import evaluate_governance_package
from autoresearch_agent.packs.skill_research.evaluators.resource_pack import evaluate_resource_package
from autoresearch_agent.packs.skill_research.evaluators.safety_pack import evaluate_safety_package
from autoresearch_agent.packs.skill_research.evaluators.trigger_pack import evaluate_trigger_package
from skill_contract.validators.package import validate_skill_package
from skill_contract.bundler.source_bundle import build_source_bundle


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _slugify(value: str, *, fallback: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized or fallback


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _text_summary(payload: dict[str, Any] | None, *, fallback: str) -> str:
    if not payload:
        return fallback
    for key in ("summary", "problem", "title", "task", "description"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return fallback


def _scalar_safe_text(value: str) -> str:
    return " ".join(str(value).replace(":", " -").split())


def build_candidate_payload(
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
) -> dict[str, Any]:
    workflow = dict(workflow or {})
    transcript = dict(transcript or {})
    failure = dict(failure or {})

    slug = _slugify(skill_name, fallback="candidate-skill")
    candidate_id = failure.get("candidate_id") or f"{slug}-candidate"
    recurring_job = _text_summary(workflow, fallback=f"Repeatable workflow for {skill_name}")
    problem_statement = _scalar_safe_text(
        _text_summary(
        failure or transcript,
        fallback=f"Package {skill_name} as a reusable governed skill instead of a one-off response.",
        )
    )
    trigger_description = _scalar_safe_text(
        workflow.get("trigger_description")
        or failure.get("trigger_description")
        or f"Use when the request matches the recurring workflow: {recurring_job}."
    ).strip()
    outputs = list(workflow.get("outputs", []) or ["generated package", "gate summary", "submission bundle"])
    owns = list(workflow.get("owns", []) or ["skill packaging", "trigger routing", "evaluation bundle generation"])
    not_owns = list(
        workflow.get("does_not_own", [])
        or ["runtime execution internals", "registry schema internals"]
    )
    target_user = str(workflow.get("target_user") or transcript.get("target_user") or "platform engineer").strip()

    return {
        "schema_version": "skill.candidate.v1",
        "candidate": {
            "id": str(candidate_id),
            "slug": slug,
            "title": str(workflow.get("title") or skill_name),
            "source_kind": str(failure.get("source_kind") or "failure_iteration"),
            "created_at": _utc_date(),
            "status": "normalized",
            "editable_target": "workspace/candidate.yaml",
        },
        "sources": {
            "refs": [item for item in [workflow.get("ref"), transcript.get("ref"), failure.get("ref")] if item],
            "normalized_summary": {
                "recurring_job": recurring_job,
                "outputs": outputs,
                "exclusions": not_owns,
                "evidence_tags": [item for item in failure.get("tags", []) if isinstance(item, str)],
            },
        },
        "qualification": {
            "should_be_skill": True,
            "reasons": ["recurring_workflow", "routing_risk", "governance_matters"],
            "target_user": target_user,
            "problem_statement": problem_statement,
        },
        "skill": {
            "name": skill_name,
            "description": _scalar_safe_text(str(workflow.get("description") or problem_statement)),
            "trigger_description": trigger_description,
            "anti_triggers": ["one-off explanation", "translation only", "brainstorm only"],
            "boundary": {
                "owns": owns,
                "does_not_own": not_owns,
            },
            "workflow": {
                "inputs": list(workflow.get("inputs", []) or ["candidate spec", "source refs", "gate cases"]),
                "steps": list(workflow.get("steps", []) or ["normalize", "materialize", "evaluate", "promote"]),
                "outputs": outputs,
            },
        },
        "actions": {
            "default_action": str(workflow.get("default_action") or "materialize_package"),
            "items": [
                {
                    "id": "materialize_package",
                    "kind": "script",
                    "entry": "scripts/materialize_package.py",
                    "runtime": "python3",
                    "timeout_sec": 120,
                    "sandbox": "workspace-write",
                },
                {
                    "id": "evaluate_package",
                    "kind": "script",
                    "entry": "scripts/evaluate_package.py",
                    "runtime": "python3",
                    "timeout_sec": 120,
                    "sandbox": "workspace-write",
                },
            ],
        },
        "package": {
            "target_platforms": ["openai", "claude", "generic"],
            "include_references": True,
            "include_scripts": True,
            "include_evals": True,
            "include_reports": False,
            "layout_profile": "standard_skill_package",
        },
        "governance": {
            "owner": owner,
            "maturity_tier": str(workflow.get("maturity_tier") or "production"),
            "lifecycle_stage": str(workflow.get("lifecycle_stage") or "library"),
            "review_cadence": str(workflow.get("review_cadence") or "quarterly"),
            "context_budget_tier": str(workflow.get("context_budget_tier") or "production"),
            "risk_level": str(workflow.get("risk_level") or "medium"),
            "trust": {
                "source_tier": "local",
                "remote_inline_execution": "forbid",
                "remote_metadata_policy": "allow-metadata-only",
            },
        },
        "lab": {
            "pack_id": "skill_research",
            "gate_profile": "balanced",
            "mutation_axes": ["trigger_description", "anti_triggers", "boundary", "actions", "eval_coverage", "governance"],
            "baseline_refs": [],
            "metrics": {},
            "last_run_id": "",
        },
        "promotion": {
            "state": "draft",
            "mode": "automatic_or_manual",
            "submission_bundle": "",
            "published_skill_ref": "",
        },
        "factory_inputs": {
            "workflow": workflow,
            "transcript": transcript,
            "failure": failure,
        },
    }


def prepare_candidate_for_lab(
    project_root: str | Path,
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
    overwrite: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    config_path = root / "research.yaml"
    if not config_path.exists():
        init_project(root, project_name=skill_name, pack_id="skill_research", data_source="datasets/input.json", overwrite=True)

    candidate_path = root / "workspace" / "candidate.yaml"
    if candidate_path.exists() and not overwrite:
        raise FileExistsError(f"candidate spec already exists: {candidate_path}")

    payload = build_candidate_payload(
        skill_name=skill_name,
        workflow=workflow,
        transcript=transcript,
        failure=failure,
        owner=owner,
    )
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "project_root": str(root),
        "candidate_path": str(candidate_path),
        "candidate": payload,
    }


def _normalize_generated_package(package_root: Path) -> None:
    package_slug = package_root.name
    manifest_path = package_root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["name"] = package_slug
        manifest["updated_at"] = str(manifest.get("updated_at") or _utc_date())[:10]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    skill_md_path = package_root / "SKILL.md"
    if skill_md_path.exists():
        lines = skill_md_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.startswith("name: "):
                lines[index] = f"name: {package_slug}"
                break
        skill_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    actions_path = package_root / "actions.yaml"
    if actions_path.exists():
        payload = json.loads(json.dumps(json.loads(json.dumps({}))))
        try:
            payload = json.loads(actions_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            from skill_contract.parsers.actions import load_actions_mapping

            payload = load_actions_mapping(actions_path)
        items = payload.get("actions") or []
        if isinstance(items, list):
            for action in items:
                if isinstance(action, dict) and "allow_network" not in action:
                    action["allow_network"] = False
        actions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_factory_pipeline(
    project_root: str | Path,
    *,
    skill_name: str,
    workflow: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    owner: str = "agent-skill-platform",
    overwrite: bool = True,
) -> dict[str, Any]:
    prepared = prepare_candidate_for_lab(
        project_root,
        skill_name=skill_name,
        workflow=workflow,
        transcript=transcript,
        failure=failure,
        owner=owner,
        overwrite=overwrite,
    )
    root = Path(project_root).resolve()
    candidate_path = Path(prepared["candidate_path"])
    build_root = root / "factory_workspace"
    build_root.mkdir(parents=True, exist_ok=True)

    materialize_report = materialize_candidate(candidate_path, build_root)
    generated_dir = Path(str(materialize_report["generated_dir"])).resolve()
    _normalize_generated_package(generated_dir)

    validation = validate_skill_package(generated_dir)
    gate_reports = {
        "trigger_evaluator": evaluate_trigger_package(generated_dir),
        "action_evaluator": evaluate_action_package(generated_dir),
        "boundary_evaluator": evaluate_boundary_package(generated_dir),
        "governance_evaluator": evaluate_governance_package(generated_dir),
        "resource_evaluator": evaluate_resource_package(generated_dir),
        "safety_evaluator": evaluate_safety_package(generated_dir),
    }
    packaging_eval = skill_lab_pipeline._build_packaging_eval(generated_dir)
    metrics = skill_lab_pipeline._metrics_from_gates(generated_dir, gate_reports, packaging_eval)
    gate_summary = skill_lab_pipeline._build_gate_summary(gate_reports, packaging_eval)
    promotion_decision = skill_lab_pipeline._build_promotion_decision(
        generated_dir,
        skill_lab_pipeline._candidate_identity(prepared["candidate"]),
        gate_summary,
        metrics,
    )

    reports_root = root / "factory_workspace" / "artifacts"
    reports_root.mkdir(parents=True, exist_ok=True)
    _json_write(reports_root / "gate_summary.json", gate_summary)
    _json_write(reports_root / "promotion_decision.json", promotion_decision)
    _json_write(reports_root / "packaging_eval.json", packaging_eval)
    _json_write(reports_root / "metrics.json", metrics)
    _json_write(reports_root / "validation_report.json", validation.model_dump())
    for name, report in gate_reports.items():
        _json_write(reports_root / f"{name}.json", report)

    bundle_artifact = build_source_bundle(generated_dir, root / "factory_workspace" / "bundles")
    return {
        "ok": gate_summary["ok"] and bool(validation.ok),
        "project_root": str(root),
        "candidate_path": str(candidate_path),
        "generated_dir": str(generated_dir),
        "bundle_path": str(bundle_artifact.path),
        "bundle_sha256": bundle_artifact.sha256,
        "bundle_size": bundle_artifact.path.stat().st_size,
        "validation": validation.model_dump(),
        "gate_summary": gate_summary,
        "promotion_decision": promotion_decision,
        "metrics": metrics,
        "artifact_root": str(reports_root),
    }
