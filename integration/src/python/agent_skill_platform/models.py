from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PromotionSubmission:
    candidate_id: str
    candidate_slug: str
    run_id: str
    bundle_path: str
    bundle_sha256: str
    manifest: dict[str, Any] = field(default_factory=dict)
    evaluation_summary: dict[str, Any] = field(default_factory=dict)
    regression_report_ref: str | None = None
    governance_report_ref: str | None = None
    safety_verdict: str = "unknown"
    promotion_decision: str = ""
    recommended_rollout_strategy: str = "manual"
    submitted_at: str = field(default_factory=_utc_now)
    submission_manifest_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_slug": self.candidate_slug,
            "run_id": self.run_id,
            "bundle_path": self.bundle_path,
            "bundle_sha256": self.bundle_sha256,
            "manifest": dict(self.manifest),
            "evaluation_summary": dict(self.evaluation_summary),
            "regression_report_ref": self.regression_report_ref,
            "governance_report_ref": self.governance_report_ref,
            "safety_verdict": self.safety_verdict,
            "promotion_decision": self.promotion_decision,
            "recommended_rollout_strategy": self.recommended_rollout_strategy,
            "submitted_at": self.submitted_at,
            "submission_manifest_path": self.submission_manifest_path,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_skill_lab_run(cls, project_root: str | Path, run_id: str) -> "PromotionSubmission":
        from autoresearch_agent.cli.runtime import submit_promotion
        from autoresearch_agent.core.runtime import RuntimeManager

        root = Path(project_root).resolve()
        payload = submit_promotion(root, run_id)
        run = RuntimeManager(root).get_run(run_id)

        submission_root = Path(str(payload["submission_root"])).resolve()
        package_path = Path(str(payload["package_path"])).resolve()
        artifacts_dir = run.run_dir / "artifacts"
        generated_manifest = _read_json(artifacts_dir / "generated_skill_package" / "manifest.json")
        gate_summary = _read_json(artifacts_dir / "gate_summary.json")
        governance_eval = _read_json(artifacts_dir / "governance_eval.json")
        safety_eval = _read_json(artifacts_dir / "safety_eval.json")
        promotion_decision = _read_json(artifacts_dir / "promotion_decision.json")
        submission_manifest = _read_json(Path(str(payload["submission_manifest_path"])))

        recommendation = str(promotion_decision.get("mode") or "manual")
        if recommendation == "automatic":
            rollout = "automatic_promote"
        else:
            rollout = "manual_review"

        return cls(
            candidate_id=str(payload.get("candidate_id") or run.manifest.get("candidate_id", "")),
            candidate_slug=str(payload.get("candidate_slug") or run.manifest.get("candidate_slug", "")),
            run_id=run_id,
            bundle_path=str(package_path),
            bundle_sha256=_sha256_file(package_path),
            manifest=generated_manifest,
            evaluation_summary={
                "gate_summary": gate_summary,
                "metrics": dict(run.result.get("metrics", {}) or {}),
            },
            regression_report_ref=str((artifacts_dir / "report.md").resolve()) if (artifacts_dir / "report.md").exists() else None,
            governance_report_ref=str((artifacts_dir / "governance_eval.json").resolve()) if governance_eval else None,
            safety_verdict="pass" if bool(safety_eval.get("ok")) else "fail",
            promotion_decision=str(promotion_decision.get("decision", "")),
            recommended_rollout_strategy=rollout,
            submitted_at=str(submission_manifest.get("submitted_at") or _utc_now()),
            submission_manifest_path=str(Path(str(payload["submission_manifest_path"])).resolve()),
            metadata={
                "submission_root": str(submission_root),
                "gate_summary_path": str((artifacts_dir / "gate_summary.json").resolve()),
                "promotion_decision_path": str((artifacts_dir / "promotion_decision.json").resolve()),
            },
        )
