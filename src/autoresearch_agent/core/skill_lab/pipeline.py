from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import json
import shutil

from autoresearch_agent.core.packs import PackManifest, load_pack_entrypoint_module
from autoresearch_agent.core.packs.loader import load_document
from autoresearch_agent.core.runtime.state_store import atomic_write_json
from autoresearch_agent.core.artifacts.writers import write_text


REQUIRED_PACKAGE_FILES = (
    "SKILL.md",
    "manifest.json",
    "actions.yaml",
    "agents/interface.yaml",
)

EVALUATOR_SPECS = {
    "trigger_evaluator": ("evaluate_trigger_package", "trigger_eval.json"),
    "action_evaluator": ("evaluate_action_package", "action_eval.json"),
    "boundary_evaluator": ("evaluate_boundary_package", "boundary_eval.json"),
    "governance_evaluator": ("evaluate_governance_package", "governance_eval.json"),
    "resource_evaluator": ("evaluate_resource_package", "resource_eval.json"),
    "safety_evaluator": ("evaluate_safety_package", "safety_eval.json"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (project_root / path).resolve()


def _editable_target_path(project_root: Path, spec: dict[str, Any]) -> Path:
    editable_targets = spec.get("search", {}).get("editable_targets", []) or ["workspace/candidate.yaml"]
    return _resolve_project_path(project_root, str(editable_targets[0]))


def _load_candidate(candidate_path: Path) -> dict[str, Any]:
    payload = load_document(candidate_path)
    if not isinstance(payload, dict):
        raise ValueError(f"candidate spec must be a mapping: {candidate_path}")
    return payload


def _candidate_identity(candidate: dict[str, Any]) -> dict[str, str]:
    candidate_info = candidate.get("candidate", {})
    skill = candidate.get("skill", {})
    slug = str(candidate_info.get("slug", "") or skill.get("name", "") or "candidate").strip().replace(" ", "-").lower()
    return {
        "id": str(candidate_info.get("id", "") or slug),
        "slug": slug or "candidate",
        "title": str(candidate_info.get("title", "") or skill.get("name", "") or "Candidate Skill"),
    }


def _materialize(manifest: PackManifest, candidate_path: Path, build_root: Path) -> Path:
    module = load_pack_entrypoint_module(manifest, "builder_module")
    materialize = getattr(module, "materialize_candidate")
    report = materialize(candidate_path, build_root)
    generated_dir = Path(str(report.get("generated_dir", ""))).resolve()
    if not generated_dir.exists():
        raise FileNotFoundError(f"materialized package not found: {generated_dir}")
    return generated_dir


def _run_evaluators(manifest: PackManifest, package_dir: Path) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for entrypoint, (function_name, _) in EVALUATOR_SPECS.items():
        module = load_pack_entrypoint_module(manifest, entrypoint)
        evaluator = getattr(module, function_name)
        reports[entrypoint] = evaluator(package_dir)
    return reports


def _parse_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _parse_actions_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = load_document(path)
    actions = payload.get("actions", []) if isinstance(payload, dict) else []
    return [item for item in actions if isinstance(item, dict)]


def _build_packaging_eval(package_dir: Path) -> dict[str, Any]:
    missing = [relative for relative in REQUIRED_PACKAGE_FILES if not (package_dir / relative).exists()]
    script_files = sorted(str(path.relative_to(package_dir)) for path in (package_dir / "scripts").rglob("*") if path.is_file()) if (package_dir / "scripts").exists() else []
    eval_files = sorted(str(path.relative_to(package_dir)) for path in (package_dir / "evals").rglob("*") if path.is_file()) if (package_dir / "evals").exists() else []
    return {
        "ok": not missing,
        "required_files_present": not missing,
        "missing_files": missing,
        "script_file_count": len(script_files),
        "eval_file_count": len(eval_files),
        "package_dir": str(package_dir),
    }


def _metrics_from_gates(package_dir: Path, gate_reports: dict[str, dict[str, Any]], packaging_eval: dict[str, Any]) -> dict[str, Any]:
    actions = _parse_actions_yaml(package_dir / "actions.yaml")
    manifest_payload = _parse_json_file(package_dir / "manifest.json")
    trigger_signal = (gate_reports.get("trigger_evaluator") or {}).get("signal", {})
    boundary_markers = (gate_reports.get("boundary_evaluator") or {}).get("boundary_markers", {})
    governance_score = 0.0
    if manifest_payload.get("owner"):
        governance_score += 0.35
    if manifest_payload.get("review_cadence"):
        governance_score += 0.25
    if manifest_payload.get("maturity_tier"):
        governance_score += 0.2
    if manifest_payload.get("lifecycle_stage"):
        governance_score += 0.2
    return {
        "trigger_precision": 1.0 if trigger_signal.get("has_trigger_description") else 0.0,
        "boundary_quality": 1.0 if boundary_markers.get("owns") and boundary_markers.get("does_not_own") else 0.0,
        "action_contract_completeness": 1.0 if actions else 0.0,
        "governance_score": round(governance_score, 3),
        "resource_budget_ok": bool((gate_reports.get("resource_evaluator") or {}).get("ok", False)),
        "safety_score": 1.0 if bool((gate_reports.get("safety_evaluator") or {}).get("ok", False)) else 0.0,
        "packaging_score": 1.0 if packaging_eval.get("ok") else 0.0,
    }


def _build_gate_summary(gate_reports: dict[str, dict[str, Any]], packaging_eval: dict[str, Any]) -> dict[str, Any]:
    gates = {
        "trigger": bool((gate_reports.get("trigger_evaluator") or {}).get("ok", False)),
        "action": bool((gate_reports.get("action_evaluator") or {}).get("ok", False)),
        "boundary": bool((gate_reports.get("boundary_evaluator") or {}).get("ok", False))
        and bool((gate_reports.get("boundary_evaluator") or {}).get("boundary_markers", {}).get("owns"))
        and bool((gate_reports.get("boundary_evaluator") or {}).get("boundary_markers", {}).get("does_not_own")),
        "governance": bool((gate_reports.get("governance_evaluator") or {}).get("ok", False)),
        "resource": bool((gate_reports.get("resource_evaluator") or {}).get("ok", False)),
        "safety": bool((gate_reports.get("safety_evaluator") or {}).get("ok", False)),
        "packaging": bool(packaging_eval.get("ok", False)),
    }
    return {
        "ok": all(gates.values()),
        "gates": gates,
        "failed_gates": [name for name, passed in gates.items() if not passed],
    }


def _build_promotion_decision(package_dir: Path, identity: dict[str, str], gate_summary: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    actions = _parse_actions_yaml(package_dir / "actions.yaml")
    manual_review = any(str(item.get("sandbox", "")).strip() not in {"", "read-only"} for item in actions)
    if gate_summary["ok"] and not manual_review:
        state = "gate_passed"
        decision = "automatic_promote"
        mode = "automatic"
    elif gate_summary["ok"]:
        state = "promotion_pending"
        decision = "manual_review"
        mode = "manual"
    else:
        state = "gate_failed"
        decision = "blocked"
        mode = "automatic"
    reasons = [f"{name}_gate_passed" for name, passed in gate_summary["gates"].items() if passed]
    reasons.extend(f"{name}_gate_failed" for name in gate_summary["failed_gates"])
    if manual_review:
        reasons.append("manual_review_required_due_to_action_sandbox")
    return {
        "candidate_id": identity["id"],
        "candidate_slug": identity["slug"],
        "state": state,
        "decision": decision,
        "mode": mode,
        "reasons": reasons,
        "scores": metrics,
    }


def _write_gate_artifacts(
    artifacts_dir: Path,
    gate_reports: dict[str, dict[str, Any]],
    packaging_eval: dict[str, Any],
    gate_summary: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> None:
    for entrypoint, (_, filename) in EVALUATOR_SPECS.items():
        atomic_write_json(artifacts_dir / filename, gate_reports[entrypoint])
    route_scorecard = {
        "ok": bool((gate_reports.get("trigger_evaluator") or {}).get("ok", False)),
        "summary": {
            "misroute_count": 0 if (gate_reports.get("trigger_evaluator") or {}).get("ok", False) else 1,
            "ambiguous_case_count": 0,
        },
        "route_stats": {
            "candidate": {
                "precision": 1.0 if (gate_reports.get("trigger_evaluator") or {}).get("ok", False) else 0.0,
                "recall": 1.0 if (gate_reports.get("trigger_evaluator") or {}).get("ok", False) else 0.0,
                "average_margin": 1.0 if (gate_reports.get("trigger_evaluator") or {}).get("ok", False) else 0.0,
            }
        },
    }
    atomic_write_json(artifacts_dir / "route_scorecard.json", route_scorecard)
    atomic_write_json(artifacts_dir / "packaging_eval.json", packaging_eval)
    atomic_write_json(artifacts_dir / "gate_summary.json", gate_summary)
    atomic_write_json(artifacts_dir / "promotion_decision.json", promotion_decision)


def _report_text(
    identity: dict[str, str],
    candidate: dict[str, Any],
    gate_summary: dict[str, Any],
    promotion_decision: dict[str, Any],
    metrics: dict[str, Any],
) -> str:
    lines = [
        f"candidate_id: {identity['id']}",
        f"candidate_slug: {identity['slug']}",
        f"skill_name: {candidate.get('skill', {}).get('name', '')}",
        f"trigger_description: {candidate.get('skill', {}).get('trigger_description', '')}",
        "",
        "gate_summary:",
    ]
    for gate, passed in gate_summary["gates"].items():
        lines.append(f"- {gate}: {passed}")
    lines.extend(
        [
            "",
            "metrics:",
        ]
    )
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            f"promotion_decision: {promotion_decision['decision']}",
            f"promotion_mode: {promotion_decision['mode']}",
            f"promotion_state: {promotion_decision['state']}",
        ]
    )
    return "\n".join(lines) + "\n"


def validate_skill_project(project_root: Path, spec: dict[str, Any], manifest: PackManifest) -> dict[str, Any]:
    candidate_path = _editable_target_path(project_root, spec)
    candidate = _load_candidate(candidate_path)
    identity = _candidate_identity(candidate)
    with TemporaryDirectory(prefix="skill-lab-validate-") as tempdir:
        build_root = Path(tempdir)
        generated_dir = _materialize(manifest, candidate_path, build_root)
        gate_reports = _run_evaluators(manifest, generated_dir)
        packaging_eval = _build_packaging_eval(generated_dir)
        gate_summary = _build_gate_summary(gate_reports, packaging_eval)
        metrics = _metrics_from_gates(generated_dir, gate_reports, packaging_eval)
    return {
        "ok": gate_summary["ok"],
        "project_root": str(project_root),
        "pack": {
            "id": manifest.pack_id,
            "name": manifest.name,
            "version": manifest.version,
            "allowed_axes": manifest.allowed_axes,
        },
        "candidate": {
            "path": str(candidate_path),
            "candidate_id": identity["id"],
            "candidate_slug": identity["slug"],
            "skill_name": candidate.get("skill", {}).get("name", ""),
        },
        "gate_summary": gate_summary,
        "metrics": metrics,
    }


def run_skill_lab(project_root: Path, spec: dict[str, Any], manifest: PackManifest, run_dir: Path, artifacts_dir: Path) -> dict[str, Any]:
    candidate_path = _editable_target_path(project_root, spec)
    candidate = _load_candidate(candidate_path)
    identity = _candidate_identity(candidate)

    candidate_artifact = artifacts_dir / "candidate.yaml"
    candidate_artifact.write_text(candidate_path.read_text(encoding="utf-8"), encoding="utf-8")

    with TemporaryDirectory(prefix="skill-lab-run-") as tempdir:
        generated_source = _materialize(manifest, candidate_path, Path(tempdir))
        generated_target = artifacts_dir / "generated_skill_package"
        if generated_target.exists():
            shutil.rmtree(generated_target)
        shutil.copytree(generated_source, generated_target)

    gate_reports = _run_evaluators(manifest, generated_target)
    packaging_eval = _build_packaging_eval(generated_target)
    gate_summary = _build_gate_summary(gate_reports, packaging_eval)
    metrics = _metrics_from_gates(generated_target, gate_reports, packaging_eval)
    promotion_decision = _build_promotion_decision(generated_target, identity, gate_summary, metrics)
    _write_gate_artifacts(artifacts_dir, gate_reports, packaging_eval, gate_summary, promotion_decision)

    iteration_history = [
        {
            "iteration": 1,
            "candidate_id": identity["id"],
            "candidate_slug": identity["slug"],
            "gates": gate_summary["gates"],
            "metrics": metrics,
            "promotion_decision": promotion_decision["decision"],
            "updated_at": _now_iso(),
        }
    ]
    atomic_write_json(artifacts_dir / "iteration_history.json", iteration_history)
    atomic_write_json(
        artifacts_dir / "candidate_patch.json",
        {
            "candidate_id": identity["id"],
            "candidate_slug": identity["slug"],
            "changed_fields": [],
            "source_path": str(candidate_path),
        },
    )
    report_text = _report_text(identity, candidate, gate_summary, promotion_decision, metrics)
    write_text(artifacts_dir / "report.md", report_text)

    result = {
        "schema_version": "skill.lab.result.v1",
        "candidate_id": identity["id"],
        "candidate_slug": identity["slug"],
        "status": promotion_decision["state"],
        "gate_passed": gate_summary["ok"],
        "metrics": metrics,
        "gate_summary": gate_summary,
        "promotion": promotion_decision,
    }
    summary = {
        "schema_version": "skill.lab.summary.v1",
        "candidate_id": identity["id"],
        "candidate_slug": identity["slug"],
        "status": promotion_decision["state"],
        "gate_passed": gate_summary["ok"],
        "promotion_decision": promotion_decision["decision"],
        "updated_at": _now_iso(),
        "metrics": metrics,
    }
    manifest_fields = {
        "candidate_id": identity["id"],
        "candidate_slug": identity["slug"],
        "candidate_status": promotion_decision["state"],
        "gate_profile": str(candidate.get("lab", {}).get("gate_profile", "balanced") or "balanced"),
        "submission_ready": gate_summary["ok"],
    }
    return {
        "result": result,
        "summary": summary,
        "manifest_fields": manifest_fields,
    }
