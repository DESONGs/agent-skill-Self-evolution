from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list_of_str(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item))
    if value is None:
        return ()
    text = str(value).strip()
    return (text,) if text else ()


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


def _normalize_lineage(base: Mapping[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
    lineage = _as_dict(base)
    for key, value in fields.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            lineage[key] = text
    return lineage


def _merge_lineage_metadata(
    metadata: Mapping[str, Any] | None,
    lineage: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    merged_metadata = _as_dict(metadata)
    normalized_lineage = _normalize_lineage(
        lineage,
        case_id=merged_metadata.get("case_id"),
        proposal_id=merged_metadata.get("proposal_id"),
        decision_mode=merged_metadata.get("decision_mode"),
        candidate_id=merged_metadata.get("candidate_id"),
        candidate_slug=merged_metadata.get("candidate_slug"),
        run_id=merged_metadata.get("run_id"),
    )
    if normalized_lineage:
        merged_metadata["lineage"] = dict(normalized_lineage)
        for key in ("case_id", "proposal_id", "decision_mode", "candidate_id", "candidate_slug", "run_id"):
            if key in normalized_lineage:
                merged_metadata[key] = normalized_lineage[key]
    return merged_metadata, normalized_lineage


@dataclass(frozen=True)
class CaseSource:
    run_id: str
    skill_id: str
    version_id: str | None = None
    action_id: str = ""
    mode: str = ""
    feedback_ref: str | None = None
    artifact_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "version_id": self.version_id,
            "action_id": self.action_id,
            "mode": self.mode,
            "feedback_ref": self.feedback_ref,
            "artifact_count": self.artifact_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseSource":
        return cls(
            run_id=str(data.get("run_id", "")),
            skill_id=str(data.get("skill_id", "")),
            version_id=data.get("version_id"),
            action_id=str(data.get("action_id", "")),
            mode=str(data.get("mode", "")),
            feedback_ref=data.get("feedback_ref"),
            artifact_count=int(data.get("artifact_count", 0) or 0),
        )


@dataclass(frozen=True)
class CasePattern:
    problem_type: str
    summary: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_type": self.problem_type,
            "summary": self.summary,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CasePattern":
        return cls(
            problem_type=str(data.get("problem_type", "")),
            summary=str(data.get("summary", "")),
            tags=_as_list_of_str(data.get("tags")),
        )


@dataclass(frozen=True)
class CaseBoundary:
    trigger_context: tuple[str, ...] = ()
    anti_trigger_context: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_context": list(self.trigger_context),
            "anti_trigger_context": list(self.anti_trigger_context),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseBoundary":
        return cls(
            trigger_context=_as_list_of_str(data.get("trigger_context")),
            anti_trigger_context=_as_list_of_str(data.get("anti_trigger_context")),
        )


@dataclass(frozen=True)
class CaseRecovery:
    worked: bool
    recovery_path: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "worked": self.worked,
            "recovery_path": list(self.recovery_path),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseRecovery":
        return cls(
            worked=bool(data.get("worked", False)),
            recovery_path=_as_list_of_str(data.get("recovery_path")),
        )


@dataclass(frozen=True)
class CaseDelta:
    recommended_evolution: str
    target_layer: str
    patch_targets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_evolution": self.recommended_evolution,
            "target_layer": self.target_layer,
            "patch_targets": list(self.patch_targets),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseDelta":
        return cls(
            recommended_evolution=str(data.get("recommended_evolution", "")),
            target_layer=str(data.get("target_layer", "")),
            patch_targets=_as_list_of_str(data.get("patch_targets")),
        )


@dataclass(frozen=True)
class CaseEvidence:
    feedback_ref: str | None = None
    artifact_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_ref": self.feedback_ref,
            "artifact_refs": list(self.artifact_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseEvidence":
        return cls(
            feedback_ref=data.get("feedback_ref"),
            artifact_refs=_as_list_of_str(data.get("artifact_refs")),
            metadata=_as_dict(data.get("metadata")),
        )


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    source: CaseSource
    pattern: CasePattern
    boundary: CaseBoundary = field(default_factory=CaseBoundary)
    recovery: CaseRecovery = field(default_factory=lambda: CaseRecovery(worked=False))
    delta: CaseDelta = field(default_factory=lambda: CaseDelta(recommended_evolution="patch", target_layer="scripts"))
    evidence: CaseEvidence = field(default_factory=CaseEvidence)
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "source": self.source.to_dict(),
            "pattern": self.pattern.to_dict(),
            "boundary": self.boundary.to_dict(),
            "recovery": self.recovery.to_dict(),
            "delta": self.delta.to_dict(),
            "evidence": self.evidence.to_dict(),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CaseRecord":
        return cls(
            case_id=str(data.get("case_id", "")),
            source=CaseSource.from_dict(_as_dict(data.get("source"))),
            pattern=CasePattern.from_dict(_as_dict(data.get("pattern"))),
            boundary=CaseBoundary.from_dict(_as_dict(data.get("boundary"))),
            recovery=CaseRecovery.from_dict(_as_dict(data.get("recovery"))),
            delta=CaseDelta.from_dict(_as_dict(data.get("delta"))),
            evidence=CaseEvidence.from_dict(_as_dict(data.get("evidence"))),
            created_at=str(data.get("created_at", _utc_now())),
            metadata=_as_dict(data.get("metadata")),
        )

    @classmethod
    def from_feedback(
        cls,
        feedback: Any,
        *,
        artifact_refs: Sequence[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "CaseRecord":
        feedback_payload = feedback.to_dict() if hasattr(feedback, "to_dict") else _as_dict(feedback)
        feedback_meta = _as_dict(feedback_payload.get("metadata"))
        extra_meta = _as_dict(metadata)
        merged_meta = {**feedback_meta, **extra_meta}
        success = bool(feedback_payload.get("success", False))
        run_id = str(feedback_payload.get("run_id", ""))
        skill_id = str(feedback_payload.get("skill_id", ""))
        action_id = str(feedback_payload.get("action_id", ""))
        version_id = feedback_payload.get("version_id")
        artifact_values = artifact_refs if artifact_refs is not None else merged_meta.get("artifact_refs", [])
        normalized_artifacts = _as_list_of_str(artifact_values)
        summary = str(
            merged_meta.get("summary")
            or merged_meta.get("problem_summary")
            or merged_meta.get("message")
            or (feedback_payload.get("error_code") or "")
            or ("execution succeeded" if success else "execution failed")
        )
        problem_type = str(merged_meta.get("problem_type") or ("success" if success else "execution_failure"))
        trigger_context = _as_list_of_str(merged_meta.get("trigger_context") or [skill_id, action_id, version_id])
        anti_trigger_context = _as_list_of_str(
            merged_meta.get("anti_trigger_context") or ([feedback_payload.get("error_code")] if feedback_payload.get("error_code") else [])
        )
        recovery_path = _as_list_of_str(merged_meta.get("recovery_path") or (["runtime_feedback"] if success else []))
        recommended_evolution = str(merged_meta.get("recommended_evolution") or ("ignore" if success else "patch"))
        target_layer = str(merged_meta.get("target_layer") or ("none" if success else "scripts"))
        patch_targets = _as_list_of_str(merged_meta.get("patch_targets"))
        case_id = str(merged_meta.get("case_id") or f"case-{run_id}-{action_id}".strip("-"))
        return cls(
            case_id=case_id,
            source=CaseSource(
                run_id=run_id,
                skill_id=skill_id,
                version_id=version_id,
                action_id=action_id,
                mode=str(feedback_payload.get("mode", "")),
                feedback_ref=str(merged_meta.get("feedback_ref") or run_id or case_id),
                artifact_count=int(feedback_payload.get("artifact_count", len(normalized_artifacts)) or len(normalized_artifacts)),
            ),
            pattern=CasePattern(
                problem_type=problem_type,
                summary=summary,
                tags=_as_list_of_str(merged_meta.get("tags")),
            ),
            boundary=CaseBoundary(
                trigger_context=trigger_context,
                anti_trigger_context=anti_trigger_context,
            ),
            recovery=CaseRecovery(
                worked=success,
                recovery_path=recovery_path,
            ),
            delta=CaseDelta(
                recommended_evolution=recommended_evolution,
                target_layer=target_layer,
                patch_targets=patch_targets,
            ),
            evidence=CaseEvidence(
                feedback_ref=str(merged_meta.get("feedback_ref") or run_id or case_id),
                artifact_refs=normalized_artifacts,
                metadata=merged_meta,
            ),
            metadata=merged_meta,
        )


@dataclass(frozen=True)
class EvolutionDecision:
    mode: str
    reason: str
    target_layer: str
    confidence: float = 0.0
    patch_targets: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "reason": self.reason,
            "target_layer": self.target_layer,
            "confidence": self.confidence,
            "patch_targets": list(self.patch_targets),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvolutionDecision":
        return cls(
            mode=str(data.get("mode", "")),
            reason=str(data.get("reason", "")),
            target_layer=str(data.get("target_layer", "")),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            patch_targets=_as_list_of_str(data.get("patch_targets")),
            metadata=_as_dict(data.get("metadata")),
            created_at=str(data.get("created_at", _utc_now())),
        )

    @classmethod
    def patch_first(cls, case: CaseRecord) -> "EvolutionDecision":
        if case.recovery.worked:
            return cls(
                mode="ignore",
                reason="case already recovered successfully",
                target_layer=case.delta.target_layer,
                confidence=0.2,
                patch_targets=case.delta.patch_targets,
                metadata={"case_id": case.case_id},
            )
        return cls(
            mode="patch",
            reason=case.pattern.summary or case.pattern.problem_type or "runtime regression requires a patch",
            target_layer=case.delta.target_layer or "scripts",
            confidence=0.85,
            patch_targets=case.delta.patch_targets,
            metadata={"case_id": case.case_id},
        )


@dataclass(frozen=True)
class CandidateProposal:
    proposal_id: str
    case: CaseRecord
    decision: EvolutionDecision
    target_skill_name: str
    target_layer: str
    patch_targets: tuple[str, ...] = ()
    change_summary: str = ""
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def case_id(self) -> str:
        return self.case.case_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "case_id": self.case_id,
            "case": self.case.to_dict(),
            "decision": self.decision.to_dict(),
            "target_skill_name": self.target_skill_name,
            "target_layer": self.target_layer,
            "patch_targets": list(self.patch_targets),
            "change_summary": self.change_summary,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateProposal":
        case_payload = _as_dict(data.get("case"))
        case = CaseRecord.from_dict(case_payload) if case_payload else CaseRecord.from_feedback(
            {
                "run_id": str(data.get("case_id", "")),
                "skill_id": str(data.get("target_skill_name", "")),
                "action_id": str(data.get("metadata", {}).get("action_id", "")) if isinstance(data.get("metadata"), Mapping) else "",
                "success": False,
            }
        )
        decision = EvolutionDecision.from_dict(_as_dict(data.get("decision")))
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            case=case,
            decision=decision,
            target_skill_name=str(data.get("target_skill_name", case.source.skill_id)),
            target_layer=str(data.get("target_layer", decision.target_layer or case.delta.target_layer)),
            patch_targets=_as_list_of_str(data.get("patch_targets") or decision.patch_targets or case.delta.patch_targets),
            change_summary=str(data.get("change_summary", "")),
            created_at=str(data.get("created_at", _utc_now())),
            metadata=_as_dict(data.get("metadata")),
        )

    @classmethod
    def from_case(
        cls,
        case: CaseRecord,
        *,
        decision: EvolutionDecision | None = None,
        target_skill_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "CandidateProposal":
        resolved_decision = decision or EvolutionDecision.patch_first(case)
        merged_metadata = {**case.metadata, **_as_dict(metadata), **resolved_decision.metadata}
        return cls(
            proposal_id=str(merged_metadata.get("proposal_id") or f"proposal-{case.case_id}"),
            case=case,
            decision=resolved_decision,
            target_skill_name=str(target_skill_name or merged_metadata.get("target_skill_name") or case.source.skill_id),
            target_layer=str(merged_metadata.get("target_layer") or resolved_decision.target_layer or case.delta.target_layer),
            patch_targets=_as_list_of_str(merged_metadata.get("patch_targets") or resolved_decision.patch_targets or case.delta.patch_targets),
            change_summary=str(
                merged_metadata.get("change_summary")
                or case.pattern.summary
                or case.pattern.problem_type
            ),
            metadata=merged_metadata,
        )


@dataclass(frozen=True)
class OutcomeRecord:
    outcome_id: str
    case_id: str
    proposal_id: str | None = None
    status: str = "recorded"
    summary: str = ""
    result_ref: str | None = None
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "case_id": self.case_id,
            "proposal_id": self.proposal_id,
            "status": self.status,
            "summary": self.summary,
            "result_ref": self.result_ref,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OutcomeRecord":
        return cls(
            outcome_id=str(data.get("outcome_id", "")),
            case_id=str(data.get("case_id", "")),
            proposal_id=data.get("proposal_id"),
            status=str(data.get("status", "recorded")),
            summary=str(data.get("summary", "")),
            result_ref=data.get("result_ref"),
            created_at=str(data.get("created_at", _utc_now())),
            metadata=_as_dict(data.get("metadata")),
        )


@dataclass(frozen=True)
class LabPromotionResult:
    case_id: str
    decision_mode: str
    proposal_id: str | None = None
    candidate_ref: str | None = None
    promotion_submission: dict[str, Any] | None = None
    outcome_id: str = ""
    status: str = "recorded"
    case_path: str | None = None
    outcome_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "decision_mode": self.decision_mode,
            "proposal_id": self.proposal_id,
            "candidate_ref": self.candidate_ref,
            "promotion_submission": dict(self.promotion_submission) if isinstance(self.promotion_submission, Mapping) else self.promotion_submission,
            "outcome_id": self.outcome_id,
            "status": self.status,
            "case_path": self.case_path,
            "outcome_path": self.outcome_path,
            "error": self.error,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LabPromotionResult":
        promotion_submission = data.get("promotion_submission")
        return cls(
            case_id=str(data.get("case_id", "")),
            decision_mode=str(data.get("decision_mode", "")),
            proposal_id=data.get("proposal_id"),
            candidate_ref=data.get("candidate_ref"),
            promotion_submission=dict(promotion_submission) if isinstance(promotion_submission, Mapping) else promotion_submission,
            outcome_id=str(data.get("outcome_id", "")),
            status=str(data.get("status", "recorded")),
            case_path=data.get("case_path"),
            outcome_path=data.get("outcome_path"),
            error=data.get("error"),
            metadata=_as_dict(data.get("metadata")),
        )


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
    lineage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metadata, lineage = _merge_lineage_metadata(self.metadata, self.lineage)
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
            "lineage": lineage,
            "metadata": metadata,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionSubmission":
        metadata, lineage = _merge_lineage_metadata(data.get("metadata"), data.get("lineage"))
        return cls(
            candidate_id=str(data.get("candidate_id", "")),
            candidate_slug=str(data.get("candidate_slug", "")),
            run_id=str(data.get("run_id", "")),
            bundle_path=str(data.get("bundle_path", "")),
            bundle_sha256=str(data.get("bundle_sha256", "")),
            manifest=_as_dict(data.get("manifest")),
            evaluation_summary=_as_dict(data.get("evaluation_summary")),
            regression_report_ref=data.get("regression_report_ref"),
            governance_report_ref=data.get("governance_report_ref"),
            safety_verdict=str(data.get("safety_verdict", "unknown")),
            promotion_decision=str(data.get("promotion_decision", "")),
            recommended_rollout_strategy=str(data.get("recommended_rollout_strategy", "manual")),
            submitted_at=str(data.get("submitted_at", _utc_now())),
            submission_manifest_path=data.get("submission_manifest_path"),
            lineage=lineage,
            metadata=metadata,
        )

    @classmethod
    def from_skill_lab_run(
        cls,
        project_root: str | Path,
        run_id: str,
        *,
        lineage: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "PromotionSubmission":
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

        submission_metadata = _as_dict(metadata)
        candidate_id = str(payload.get("candidate_id") or run.manifest.get("candidate_id", ""))
        candidate_slug = str(payload.get("candidate_slug") or run.manifest.get("candidate_slug", ""))
        case_id = str(
            (lineage or {}).get("case_id")
            or submission_metadata.get("case_id")
            or submission_manifest.get("case_id")
            or run.manifest.get("case_id", "")
        )
        proposal_id = str(
            (lineage or {}).get("proposal_id")
            or submission_metadata.get("proposal_id")
            or submission_manifest.get("proposal_id")
            or run.manifest.get("proposal_id", "")
        )
        decision_mode = str(
            (lineage or {}).get("decision_mode")
            or submission_metadata.get("decision_mode")
            or promotion_decision.get("mode")
            or promotion_decision.get("decision_mode")
            or promotion_decision.get("decision")
            or ""
        )
        lineage_payload = _normalize_lineage(
            lineage,
            case_id=case_id,
            proposal_id=proposal_id,
            decision_mode=decision_mode,
            candidate_id=candidate_id,
            candidate_slug=candidate_slug,
            run_id=run_id,
        )
        recommendation = str(promotion_decision.get("mode") or decision_mode or "manual")
        rollout = "automatic_promote" if recommendation == "automatic" else "manual_review"

        return cls(
            candidate_id=candidate_id,
            candidate_slug=candidate_slug,
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
            lineage=lineage_payload,
            metadata={
                **submission_metadata,
                "submission_root": str(submission_root),
                "gate_summary_path": str((artifacts_dir / "gate_summary.json").resolve()),
                "promotion_decision_path": str((artifacts_dir / "promotion_decision.json").resolve()),
                "case_id": case_id or None,
                "proposal_id": proposal_id or None,
                "decision_mode": decision_mode or None,
                "candidate_id": candidate_id or None,
                "candidate_slug": candidate_slug or None,
                "lineage": lineage_payload,
            },
        )
