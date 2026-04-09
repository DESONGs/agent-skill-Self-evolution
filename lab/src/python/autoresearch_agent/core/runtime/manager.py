from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import copy
import uuid

from ..artifacts import build_artifact_index
from ..artifacts.writers import write_text
from ..datasets import load_dataset_records, profile_dataset
from ..packs.loader import find_pack_manifest
from ..search import IterationEngine
from ..skill_lab import run_skill_lab
from ..strategy import CONFIG_DEFAULTS, apply_config_to_strategy_text, build_strategy_patch, load_strategy
from .lifecycle import RuntimeStatus
from .spec import RuntimeSpecError, load_runtime_spec, normalize_runtime_spec, validate_runtime_spec
from .state_store import atomic_write_json, ensure_dir, read_json
from ..paths import project_file_path


StrategyFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


@dataclass(frozen=True)
class RuntimeRun:
    run_id: str
    status: str
    run_dir: Path
    spec: dict[str, Any]
    manifest: dict[str, Any]
    result: dict[str, Any]
    summary: dict[str, Any]
    artifacts: list[dict[str, Any]]


class RuntimeManager:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()

    def _editable_target_path(self, spec: dict[str, Any]) -> Path:
        editable_targets = spec.get("search", {}).get("editable_targets", []) or ["workspace/strategy.py"]
        return _resolve_path(self.project_root, str(editable_targets[0]))

    def _runtime_root(self, spec: dict[str, Any]) -> Path:
        project = spec.get("project", {})
        runs_dir = project.get("runs_dir", "./.autoresearch/runs")
        return _resolve_path(self.project_root, runs_dir)

    def _run_dir(self, spec: dict[str, Any], run_id: str) -> Path:
        return self._runtime_root(spec) / run_id

    def _artifacts_dir(self, spec: dict[str, Any], run_dir: Path, *, create: bool = False) -> Path:
        project = spec.get("project", {})
        configured = str(project.get("artifacts_dir", "./artifacts") or "./artifacts").strip() or "./artifacts"
        path = Path(configured)
        resolved = path.resolve() if path.is_absolute() else (run_dir / path).resolve()
        try:
            resolved.relative_to(run_dir)
        except ValueError as exc:
            raise RuntimeSpecError("project.artifacts_dir must stay within the run directory") from exc
        return ensure_dir(resolved) if create else resolved

    def _write_manifest(self, run_dir: Path, manifest: dict[str, Any]) -> None:
        atomic_write_json(run_dir / "run_manifest.json", manifest)

    def _write_spec(self, run_dir: Path, spec: dict[str, Any]) -> None:
        atomic_write_json(run_dir / "run_spec.json", spec)

    def _write_result(self, run_dir: Path, result: dict[str, Any]) -> None:
        atomic_write_json(run_dir / "result.json", result)

    def _write_summary(self, run_dir: Path, summary: dict[str, Any]) -> None:
        atomic_write_json(run_dir / "summary.json", summary)

    def _write_dataset_artifacts(
        self,
        artifacts_dir: Path,
        records: list[dict[str, Any]],
        summary: dict[str, Any],
        *,
        write_dataset_profile: bool,
    ) -> None:
        if not write_dataset_profile:
            return
        atomic_write_json(artifacts_dir / "dataset_snapshot.json", records)
        atomic_write_json(artifacts_dir / "dataset_profile.json", summary)

    def _write_report(
        self,
        artifacts_dir: Path,
        *,
        spec: dict[str, Any],
        best_result: dict[str, Any],
        best_config: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> None:
        report = "\n".join(
            [
                f"project: {spec.get('project', {}).get('name', '')}",
                f"pack: {spec.get('pack', {}).get('id', '')}",
                f"iterations: {len(history)}",
                f"fitness: {best_result.get('fitness', 0.0)}",
                f"accuracy: {best_result.get('accuracy', 0.0)}",
                f"total_pnl: {best_result.get('total_pnl', 0.0)}",
                f"confidence_threshold: {best_config.get('confidence_threshold', CONFIG_DEFAULTS['confidence_threshold'])}",
                f"bet_sizing: {best_config.get('bet_sizing', CONFIG_DEFAULTS['bet_sizing'])}",
                f"max_bet_fraction: {best_config.get('max_bet_fraction', CONFIG_DEFAULTS['max_bet_fraction'])}",
                f"prompt_factors: {best_config.get('prompt_factors', [])}",
                "",
            ]
        )
        write_text(artifacts_dir / "report.md", report)

    def _write_strategy_artifacts(self, artifacts_dir: Path, source_text: str, best_config: dict[str, Any], *, write_best_strategy: bool, write_patch: bool) -> None:
        best_text = apply_config_to_strategy_text(source_text, best_config)
        if write_best_strategy:
            write_text(artifacts_dir / "best_strategy.py", best_text)
        if write_patch:
            write_text(artifacts_dir / "strategy.patch", build_strategy_patch(source_text, best_text))

    def _build_summary(
        self,
        *,
        spec: dict[str, Any],
        profile: dict[str, Any],
        result: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema_version": "runtime_summary.v1",
            "project": spec.get("project", {}),
            "pack": spec.get("pack", {}),
            "data_profile": profile,
            "best_result": result,
            "iteration_count": len(history),
            "history_tail": history[-3:],
            "updated_at": _now_iso(),
        }

    def _read_manifest(self, run_dir: Path) -> dict[str, Any]:
        return read_json(run_dir / "run_manifest.json", {}) or {}

    def _read_spec(self, run_dir: Path) -> dict[str, Any]:
        return read_json(run_dir / "run_spec.json", {}) or {}

    def _read_result(self, run_dir: Path) -> dict[str, Any]:
        return read_json(run_dir / "result.json", {}) or {}

    def _read_summary(self, run_dir: Path) -> dict[str, Any]:
        return read_json(run_dir / "summary.json", {}) or {}

    def create_run(
        self,
        spec_input: dict[str, Any] | str | Path,
        *,
        run_id: str | None = None,
        strategy_fn: StrategyFn | None = None,
        parent_run_id: str = "",
    ) -> RuntimeRun:
        spec = load_runtime_spec(spec_input) if isinstance(spec_input, (str, Path)) else validate_runtime_spec(spec_input)
        runtime_root = self._runtime_root(spec)
        ensure_dir(runtime_root)

        resolved_run_id = run_id or _run_id()
        run_dir = ensure_dir(self._run_dir(spec, resolved_run_id))
        artifacts_dir = self._artifacts_dir(spec, run_dir, create=True)
        pack_id = str(spec.get("pack", {}).get("id", "") or "")

        if pack_id == "skill_research":
            skill_manifest = find_pack_manifest(pack_id)
            skill_run = run_skill_lab(self.project_root, spec, skill_manifest, run_dir, artifacts_dir)
            result = dict(skill_run["result"])
            summary = dict(skill_run["summary"])
            manifest = {
                "run_id": resolved_run_id,
                "status": RuntimeStatus.FINISHED,
                "created_at": _now_iso(),
                "started_at": _now_iso(),
                "finished_at": _now_iso(),
                "updated_at": _now_iso(),
                "parent_run_id": parent_run_id,
                "project_name": spec.get("project", {}).get("name", ""),
                "pack_id": pack_id,
                **dict(skill_run.get("manifest_fields") or {}),
            }
            self._write_spec(run_dir, spec)
            self._write_result(run_dir, result)
            self._write_summary(run_dir, summary)
            self._write_manifest(run_dir, manifest)
            artifacts = build_artifact_index(run_dir, artifacts_dir=artifacts_dir)
            atomic_write_json(artifacts_dir / "artifact_index.json", artifacts)
            artifacts = build_artifact_index(run_dir, artifacts_dir=artifacts_dir)
            return RuntimeRun(
                run_id=resolved_run_id,
                status=RuntimeStatus.FINISHED,
                run_dir=run_dir,
                spec=spec,
                manifest=manifest,
                result=result,
                summary=summary,
                artifacts=artifacts,
            )

        strategy_path = self._editable_target_path(spec)
        loaded_strategy = load_strategy(strategy_path)

        dataset = load_dataset_records(_resolve_path(self.project_root, spec["data"]["source"]))
        profile = profile_dataset(dataset)
        engine = IterationEngine()
        search = spec.get("search", {})
        initial_config = dict(loaded_strategy.config)
        initial_config.update(
            {k: v for k, v in search.items() if k in {"confidence_threshold", "max_bet_fraction", "bet_sizing", "prompt_factors"}}
        )
        iteration_bundle = engine.run(
            dataset,
            initial_config,
            max_iterations=int(search.get("max_iterations", 1) or 1),
            strategy_fn=strategy_fn or loaded_strategy.strategy_fn,
        )
        best_result = dict(iteration_bundle["best_result"])
        best_config = dict(iteration_bundle.get("best_config") or initial_config)
        best_result["best_config"] = best_config
        best_result["gate_passed"] = bool(iteration_bundle.get("gate_passed", False))
        best_result["gate_metrics"] = dict(iteration_bundle.get("gate_metrics") or {})
        history = iteration_bundle["history"]
        summary = self._build_summary(spec=spec, profile=profile, result=best_result, history=history)
        outputs = spec.get("outputs", {})

        self._write_spec(run_dir, spec)
        self._write_result(run_dir, best_result)
        self._write_summary(run_dir, summary)
        self._write_dataset_artifacts(
            artifacts_dir,
            dataset,
            profile,
            write_dataset_profile=bool(outputs.get("write_dataset_profile", True)),
        )
        atomic_write_json(artifacts_dir / "iteration_history.json", history)
        if outputs.get("write_report", True):
            self._write_report(artifacts_dir, spec=spec, best_result=best_result, best_config=best_config, history=history)
        if outputs.get("write_best_strategy", True) or outputs.get("write_patch", True):
            self._write_strategy_artifacts(
                artifacts_dir,
                loaded_strategy.source_text,
                best_config,
                write_best_strategy=bool(outputs.get("write_best_strategy", True)),
                write_patch=bool(outputs.get("write_patch", True)),
            )

        manifest = {
            "run_id": resolved_run_id,
            "status": RuntimeStatus.FINISHED,
            "created_at": _now_iso(),
            "started_at": _now_iso(),
            "finished_at": _now_iso(),
            "updated_at": _now_iso(),
            "parent_run_id": parent_run_id,
            "project_name": spec.get("project", {}).get("name", ""),
            "pack_id": spec.get("pack", {}).get("id", ""),
            "dataset_source": spec.get("data", {}).get("source", ""),
            "best_result_fitness": best_result.get("fitness", 0.0),
            "best_result_accuracy": best_result.get("accuracy", 0.0),
        }
        self._write_manifest(run_dir, manifest)
        artifacts = build_artifact_index(run_dir, artifacts_dir=artifacts_dir)
        atomic_write_json(artifacts_dir / "artifact_index.json", artifacts)
        artifacts = build_artifact_index(run_dir, artifacts_dir=artifacts_dir)

        return RuntimeRun(
            run_id=resolved_run_id,
            status=RuntimeStatus.FINISHED,
            run_dir=run_dir,
            spec=spec,
            manifest=manifest,
            result=best_result,
            summary=summary,
            artifacts=artifacts,
        )

    def continue_run(
        self,
        run_id: str,
        *,
        next_run_id: str | None = None,
        spec_override: dict[str, Any] | None = None,
        strategy_fn: StrategyFn | None = None,
    ) -> RuntimeRun:
        previous = self.get_run(run_id)
        spec = copy.deepcopy(previous.spec)
        if spec_override:
            spec = normalize_runtime_spec({**spec, **spec_override})
        return self.create_run(spec, run_id=next_run_id, strategy_fn=strategy_fn, parent_run_id=previous.run_id)

    def get_run(self, run_id: str) -> RuntimeRun:
        run_root = self._find_run_root(run_id)
        if run_root is None:
            raise FileNotFoundError(f"run not found: {run_id}")
        spec = self._read_spec(run_root)
        manifest = self._read_manifest(run_root)
        result = self._read_result(run_root)
        summary = self._read_summary(run_root)
        artifacts = build_artifact_index(run_root, artifacts_dir=self._artifacts_dir(spec, run_root))
        return RuntimeRun(
            run_id=run_id,
            status=str(manifest.get("status", RuntimeStatus.CREATED)),
            run_dir=run_root,
            spec=spec,
            manifest=manifest,
            result=result,
            summary=summary,
            artifacts=artifacts,
        )

    def _find_run_root(self, run_id: str) -> Path | None:
        for root in self._candidate_roots():
            run_root = root / run_id
            if run_root.exists():
                return run_root
        return None

    def _candidate_roots(self) -> list[Path]:
        roots: list[Path] = []
        spec_path = project_file_path(self.project_root)
        if spec_path.exists():
            try:
                spec = load_runtime_spec(spec_path)
            except Exception:
                spec = {}
            configured_root = self._runtime_root(spec) if isinstance(spec, dict) and spec else None
            if configured_root is not None:
                roots.append(configured_root)
        if not roots:
            roots.append((self.project_root / ".autoresearch" / "runs").resolve())
        return roots

    def status(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        best_config = run.result.get("best_config", {})
        payload = {
            "run_id": run.run_id,
            "status": run.status,
            "updated_at": run.summary.get("updated_at", run.manifest.get("updated_at", "")),
        }
        if "metrics" in run.result:
            payload["metrics"] = run.result.get("metrics", {})
            payload["gate_passed"] = bool(run.result.get("gate_passed", False))
            payload["promotion_decision"] = (run.result.get("promotion") or {}).get("decision", "")
        else:
            payload["fitness"] = run.result.get("fitness", 0.0)
            payload["accuracy"] = run.result.get("accuracy", 0.0)
            payload["best_config"] = best_config
        return payload

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        return self.get_run(run_id).artifacts

    def run(self, spec_input: dict[str, Any] | str | Path, *, run_id: str | None = None) -> RuntimeRun:
        return self.create_run(spec_input, run_id=run_id)
