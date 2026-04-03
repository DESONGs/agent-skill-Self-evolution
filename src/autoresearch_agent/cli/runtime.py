from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from autoresearch_agent.core.datasets import load_dataset_records, profile_dataset
from autoresearch_agent.core.packs import PackLoader, load_pack_entrypoint_module
from autoresearch_agent.core.paths import project_file_path, resolve_project_root
from autoresearch_agent.core.runtime import RuntimeManager
from autoresearch_agent.core.skill_lab import validate_skill_project
from autoresearch_agent.core.spec.research_config import load_research_spec
from autoresearch_agent.core.strategy import load_strategy
from autoresearch_agent.project.scaffold import scaffold_project


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)


def project_root_from_input(path: str | Path | None) -> Path:
    return resolve_project_root(path or Path.cwd())


def spec_path_from_project_root(project_root: str | Path) -> Path:
    return project_file_path(project_root)


def pack_loader() -> PackLoader:
    return PackLoader()


def _resolve_project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (project_root / path).resolve()


def _pack_summary(manifest: Any) -> dict[str, Any]:
    return {
        "id": manifest.pack_id,
        "name": manifest.name,
        "version": manifest.version,
        "allowed_axes": manifest.allowed_axes,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _submission_builder_key(manifest: Any) -> str:
    for key in (
        "submission_builder",
        "submission_builder_module",
        "submission_exporter",
        "submission_exporter_module",
    ):
        if str(manifest.entrypoints.get(key, "") or "").strip():
            return key
    return ""


def _fallback_submission_bundle(run_dir: Path, candidate_slug: str, run_id: str) -> dict[str, Any]:
    artifacts_dir = run_dir / "artifacts"
    generated_package_dir = artifacts_dir / "generated_skill_package"
    if not generated_package_dir.exists():
        raise FileNotFoundError(f"generated package missing for run: {run_id}")

    submission_root = run_dir / "submissions" / f"{candidate_slug}-{run_id}"
    if submission_root.exists():
        shutil.rmtree(submission_root)
    submission_root.mkdir(parents=True, exist_ok=True)

    package_path = submission_root / "skill-package.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in generated_package_dir.rglob("*") if path.is_file()):
            archive.write(file_path, arcname=str(file_path.relative_to(generated_package_dir.parent)))

    report_path = artifacts_dir / "report.md"
    promotion_decision_path = artifacts_dir / "promotion_decision.json"
    if report_path.exists():
        shutil.copy2(report_path, submission_root / "report.md")
    if promotion_decision_path.exists():
        shutil.copy2(promotion_decision_path, submission_root / "promotion_decision.json")

    submission_manifest = {
        "schema_version": "skill.lab.submission.v1",
        "candidate_slug": candidate_slug,
        "run_id": run_id,
        "package_path": str(package_path),
        "generated_package_dir": str(generated_package_dir),
        "report_path": str(report_path) if report_path.exists() else "",
        "submitted_at": "",
    }
    submission_manifest_path = submission_root / "submission_manifest.json"
    submission_manifest_path.write_text(json_dumps(submission_manifest) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "submission_root": str(submission_root),
        "submission_manifest_path": str(submission_manifest_path),
        "submission_manifest": submission_manifest,
        "package_path": str(package_path),
        "bundle_path": str(package_path),
    }


def _build_submission_bundle(project_root: Path, run_id: str, manifest: Any, run: Any) -> dict[str, Any]:
    candidate_slug = str(run.manifest.get("candidate_slug") or run.result.get("candidate_slug") or "candidate")
    submission_builder_key = _submission_builder_key(manifest)
    if submission_builder_key:
        module = load_pack_entrypoint_module(manifest, submission_builder_key)
        exporter = getattr(module, "export_submission_bundle")
        try:
            payload = exporter(run.run_dir)
        except TypeError:
            payload = exporter(run.run_dir, candidate_slug, run_id)
    else:
        payload = _fallback_submission_bundle(run.run_dir, candidate_slug, run_id)

    source_root_value = payload.get("submission_root") or payload.get("submission_dir")
    source_root = Path(str(source_root_value)).resolve() if source_root_value else None
    target_root = (project_root / "workspace" / "submissions" / f"{candidate_slug}-{run_id}").resolve()

    if source_root is not None and source_root.exists():
        if source_root != target_root:
            if target_root.exists():
                shutil.rmtree(target_root)
            shutil.copytree(source_root, target_root)
    else:
        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.mkdir(parents=True, exist_ok=True)

    run_artifacts_dir = run.run_dir / "artifacts"
    for artifact_name in ("report.md", "promotion_decision.json"):
        source = run_artifacts_dir / artifact_name
        target = target_root / artifact_name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)

    manifest_path = target_root / "submission_manifest.json"
    if manifest_path.exists():
        submission_manifest = _read_json(manifest_path)
    else:
        package_name = Path(str(payload.get("package_path") or payload.get("bundle_path") or "skill-package.zip")).name
        submission_manifest = {
            "schema_version": "skill.lab.submission.v1",
            "candidate_id": str(run.manifest.get("candidate_id") or run.result.get("candidate_id") or ""),
            "candidate_slug": candidate_slug,
            "run_id": run_id,
            "package_path": str((target_root / package_name).resolve()),
            "report_path": str((target_root / "report.md").resolve()) if (target_root / "report.md").exists() else "",
            "submitted_at": "",
        }
        manifest_path.write_text(json_dumps(submission_manifest) + "\n", encoding="utf-8")

    package_name = Path(str(payload.get("package_path") or payload.get("bundle_path") or "skill-package.zip")).name
    package_path = (target_root / package_name).resolve()
    return {
        "ok": True,
        "run_id": run_id,
        "candidate_id": str(run.manifest.get("candidate_id") or run.result.get("candidate_id") or ""),
        "candidate_slug": candidate_slug,
        "submission_root": str(target_root),
        "package_path": str(package_path),
        "submission_manifest_path": str(manifest_path),
        "submission_manifest": submission_manifest,
    }


def install_pack_snapshot(project_root: str | Path, pack_id: str) -> Path:
    root = project_root_from_input(project_root)
    manifest = pack_loader().load(pack_id)
    state_dir = root / ".autoresearch" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / f"{manifest.pack_id}.pack.json"
    target.write_text(json_dumps(manifest.to_dict()) + "\n", encoding="utf-8")
    return target


def init_project(
    project_root: str | Path,
    *,
    project_name: str | None,
    pack_id: str,
    data_source: str,
    overwrite: bool,
) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    result = scaffold_project(
        root,
        project_name=project_name,
        pack_id=pack_id,
        data_source=data_source,
        overwrite=overwrite,
    )
    snapshot = install_pack_snapshot(root, pack_id)
    return {
        "project_root": str(root),
        "config_path": str(result["config_path"]),
        "pack_snapshot": str(snapshot),
        "created_paths": [str(path) for path in result["created_paths"]],
    }


def validate_project(project_root: str | Path) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    spec_path = spec_path_from_project_root(root)
    spec = load_research_spec(spec_path)
    manifest = pack_loader().load(str(spec["pack"]["id"]))

    if manifest.pack_id == "skill_research":
        payload = validate_skill_project(root, spec, manifest)
        payload["spec_path"] = str(spec_path)
        return payload

    dataset_path = _resolve_project_path(root, str(spec["data"]["source"]))
    records = load_dataset_records(dataset_path) if dataset_path.exists() else []
    dataset_profile = profile_dataset(records) if records else {"num_records": 0}
    editable_targets = spec.get("search", {}).get("editable_targets", []) or manifest.editable_targets or ["workspace/strategy.py"]
    editable_target_path = _resolve_project_path(root, str(editable_targets[0]))
    loaded_strategy = load_strategy(editable_target_path) if editable_target_path.exists() else None

    return {
        "ok": True,
        "project_root": str(root),
        "spec_path": str(spec_path),
        "pack": _pack_summary(manifest),
        "dataset": {
            "source": str(dataset_path),
            "num_records": dataset_profile.get("num_records", 0),
            "profile": dataset_profile,
        },
        "strategy": None if loaded_strategy is None else {"path": str(editable_target_path), "base_config": loaded_strategy.config},
    }


def run_project(project_root: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    spec_path = spec_path_from_project_root(root)
    run = RuntimeManager(root).run(spec_path, run_id=run_id or None)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "run_dir": str(run.run_dir),
        "result": run.result,
        "summary": run.summary,
        "artifacts": run.artifacts,
    }


def continue_project_run(project_root: str | Path, run_id: str, *, next_run_id: str | None = None) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    run = RuntimeManager(root).continue_run(run_id, next_run_id=next_run_id or None)
    return {
        "run_id": run.run_id,
        "parent_run_id": run.manifest.get("parent_run_id", ""),
        "status": run.status,
        "run_dir": str(run.run_dir),
        "result": run.result,
    }


def get_run_status(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    return RuntimeManager(root).status(run_id)


def get_run_artifacts(project_root: str | Path, run_id: str) -> list[dict[str, Any]]:
    root = project_root_from_input(project_root)
    return RuntimeManager(root).list_artifacts(run_id)


def list_packs() -> list[dict[str, Any]]:
    return [
        {
            "pack_id": manifest.pack_id,
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "supported_formats": manifest.supported_formats,
            "allowed_axes": manifest.allowed_axes,
        }
        for manifest in pack_loader().list_packs()
    ]


def submit_promotion(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = project_root_from_input(project_root)
    spec = load_research_spec(spec_path_from_project_root(root))
    manifest = pack_loader().load(str(spec["pack"]["id"]))
    if manifest.pack_id != "skill_research":
        raise ValueError("promotion submission is only supported for skill_research projects")
    run = RuntimeManager(root).get_run(run_id)
    return _build_submission_bundle(root, run_id, manifest, run)
