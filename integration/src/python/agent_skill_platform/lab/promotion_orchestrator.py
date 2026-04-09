from __future__ import annotations

from ..bootstrap import ensure_source_layout

ensure_source_layout()

import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..models import CandidateProposal, CaseRecord, LabPromotionResult, OutcomeRecord, PromotionSubmission
from ..paths import detect_platform_paths
from .case_analyzer import CaseAnalyzer
from .case_store import CaseStore, default_backend_root
from .decider import Decider
from .outcome_store import OutcomeStore
from .proposal_adapter import ProposalAdapter


def _default_registry_root() -> Path:
    return detect_platform_paths().data_root / "registry"


def _coerce_feedback(feedback: Any) -> RunFeedbackEnvelope:
    if isinstance(feedback, RunFeedbackEnvelope):
        return feedback
    if hasattr(feedback, "to_dict"):
        return RunFeedbackEnvelope.from_dict(feedback.to_dict())
    if isinstance(feedback, Mapping):
        return RunFeedbackEnvelope.from_dict(dict(feedback))
    raise TypeError(f"Unsupported feedback payload: {type(feedback)!r}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_registry_service(root: str | Path | None) -> Any:
    registry_root = Path(root) if root is not None else _default_registry_root()
    try:
        from ..registry.service import RegistryService as registry_cls
        return registry_cls(registry_root)
    except Exception:
        pass

    class _LocalPromotionIntakeService:
        def __init__(self, intake_root: Path):
            self.root = intake_root
            self.root.mkdir(parents=True, exist_ok=True)
            self.promotions_root = self.root / "promotions"
            self.promotions_root.mkdir(parents=True, exist_ok=True)

        def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
            normalized = submission if isinstance(submission, PromotionSubmission) else PromotionSubmission.from_dict(submission)
            payload = normalized.to_dict()
            lineage = dict(payload.get("lineage") or {})
            metadata = dict(payload.get("metadata") or {})
            metadata["lineage"] = lineage
            payload["metadata"] = metadata
            request_root = self.promotions_root / normalized.candidate_slug / normalized.run_id
            request_root.mkdir(parents=True, exist_ok=True)
            payload_path = request_root / "promotion_submission.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {
                "ok": True,
                "state": "PENDING_REVIEW",
                "submission_path": str(payload_path),
                "submission": payload,
                "lineage": lineage,
            }

    return _LocalPromotionIntakeService(registry_root)


class LabPromotionOrchestrator:
    def __init__(
        self,
        *,
        backend_root: str | Path | None = None,
        registry_root: str | Path | None = None,
        registry_service: Any | None = None,
        case_store: CaseStore | None = None,
        outcome_store: OutcomeStore | None = None,
        decider: Decider | None = None,
        proposal_adapter: ProposalAdapter | None = None,
        candidate_root: str | Path | None = None,
    ):
        self.backend_root = Path(backend_root) if backend_root is not None else default_backend_root()
        self.backend_root.mkdir(parents=True, exist_ok=True)
        self.case_store = case_store or CaseStore(self.backend_root)
        self.outcome_store = outcome_store or OutcomeStore(self.backend_root)
        self.candidate_root = Path(candidate_root) if candidate_root is not None else self.backend_root / "candidates"
        self.candidate_root.mkdir(parents=True, exist_ok=True)
        self.decider = decider or Decider()
        self.proposal_adapter = proposal_adapter or ProposalAdapter()
        self.registry_service = registry_service or _build_registry_service(registry_root)
        self.case_analyzer = CaseAnalyzer()

    def analyze_feedback(
        self,
        feedback: Any,
        *,
        artifact_refs: tuple[str, ...] | list[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CaseRecord:
        normalized_feedback = _coerce_feedback(feedback)
        return self.case_analyzer.analyze(
            normalized_feedback,
            artifact_refs=artifact_refs,
            metadata=metadata,
        )

    def _store_case(self, case: CaseRecord) -> dict[str, Any]:
        return self.case_store.record_case(case)

    def _store_outcome(self, outcome: OutcomeRecord) -> dict[str, Any]:
        return self.outcome_store.record_outcome(outcome)

    def _positive_flow(
        self,
        *,
        case: CaseRecord,
        proposal: CandidateProposal,
        case_path: str | None,
        decision_mode: str,
        metadata: Mapping[str, Any] | None,
        owner: str,
        target_user: str,
        recurring_job: str | None,
        source_kind: str,
    ) -> LabPromotionResult:
        candidate_dir = self.candidate_root / case.case_id / proposal.proposal_id
        candidate_path = self.proposal_adapter.write_candidate_file(
            proposal,
            candidate_dir / "candidate.yaml",
            owner=owner,
            target_user=target_user,
            recurring_job=recurring_job,
            source_kind=source_kind,
        )
        candidate_ref = str(candidate_path)
        candidate_payload = self.proposal_adapter.to_candidate_payload(
            proposal,
            owner=owner,
            target_user=target_user,
            recurring_job=recurring_job,
            source_kind=source_kind,
        )
        candidate_hash = _sha256_file(candidate_path)
        lineage = {
            "case_id": case.case_id,
            "proposal_id": proposal.proposal_id,
            "decision_mode": decision_mode,
        }
        merged_metadata = {
            **dict(case.metadata),
            **dict(metadata or {}),
            "case_id": case.case_id,
            "proposal_id": proposal.proposal_id,
            "decision_mode": decision_mode,
            "lineage": lineage,
            "candidate_ref": candidate_ref,
            "candidate_sha256": candidate_hash,
        }
        submission = PromotionSubmission(
            candidate_id=str(candidate_payload["candidate"]["id"]),
            candidate_slug=str(candidate_payload["candidate"]["slug"]),
            run_id=case.source.run_id or proposal.proposal_id,
            bundle_path=candidate_ref,
            bundle_sha256=candidate_hash,
            manifest=candidate_payload,
            evaluation_summary={
                "case_id": case.case_id,
                "decision_mode": decision_mode,
                "decision_reason": proposal.decision.reason,
                "target_layer": proposal.target_layer,
                "change_summary": proposal.change_summary,
            },
            safety_verdict=str(dict(metadata or {}).get("safety_verdict", "unknown")),
            promotion_decision=decision_mode,
            recommended_rollout_strategy=str(dict(metadata or {}).get("rollout_strategy", "manual")),
            lineage=lineage,
            metadata=merged_metadata,
        )
        promotion_submission: dict[str, Any] | None = None
        try:
            promotion_submission = self.registry_service.submit_promotion(submission)
            outcome = OutcomeRecord(
                outcome_id=str(dict(metadata or {}).get("outcome_id") or f"outcome-{case.case_id}-{proposal.proposal_id}"),
                case_id=case.case_id,
                proposal_id=proposal.proposal_id,
                status="promoted",
                summary=proposal.change_summary or proposal.decision.reason,
                result_ref=promotion_submission.get("submission_path") or candidate_ref,
                metadata={
                    **merged_metadata,
                    "case_path": case_path,
                    "promotion_submission": promotion_submission,
                    "candidate_ref": candidate_ref,
                },
            )
            outcome_result = self._store_outcome(outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=decision_mode,
                proposal_id=proposal.proposal_id,
                candidate_ref=candidate_ref,
                promotion_submission=promotion_submission,
                outcome_id=outcome.outcome_id,
                status="promoted",
                case_path=case_path,
                outcome_path=outcome_result["outcome_path"],
                metadata={
                    **merged_metadata,
                    "case_path": case_path,
                    "outcome_path": outcome_result["outcome_path"],
                    "promotion_submission": promotion_submission,
                },
            )
        except Exception as exc:
            failure_outcome = OutcomeRecord(
                outcome_id=str(dict(metadata or {}).get("outcome_id") or f"outcome-{case.case_id}-{proposal.proposal_id}"),
                case_id=case.case_id,
                proposal_id=proposal.proposal_id,
                status="failed",
                summary=str(exc),
                result_ref=(promotion_submission or {}).get("submission_path") or candidate_ref,
                metadata={
                    **merged_metadata,
                    "case_path": case_path,
                    "promotion_submission": promotion_submission,
                    "candidate_ref": candidate_ref,
                    "error": str(exc),
                },
            )
            outcome_result = self._store_outcome(failure_outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=decision_mode,
                proposal_id=proposal.proposal_id,
                candidate_ref=candidate_ref,
                promotion_submission=promotion_submission,
                outcome_id=failure_outcome.outcome_id,
                status="failed",
                case_path=case_path,
                outcome_path=outcome_result["outcome_path"],
                error=str(exc),
                metadata={
                    **merged_metadata,
                    "case_path": case_path,
                    "outcome_path": outcome_result["outcome_path"],
                    "promotion_submission": promotion_submission,
                    "candidate_ref": candidate_ref,
                    "error": str(exc),
                },
            )

    def _ignored_flow(
        self,
        *,
        case: CaseRecord,
        proposal: CandidateProposal,
        case_path: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> LabPromotionResult:
        outcome = OutcomeRecord(
            outcome_id=str(dict(metadata or {}).get("outcome_id") or f"outcome-{case.case_id}-{proposal.proposal_id}"),
            case_id=case.case_id,
            proposal_id=proposal.proposal_id,
            status="ignored",
            summary=proposal.decision.reason or case.pattern.summary or "case ignored",
            result_ref=case_path,
            metadata={
                **dict(case.metadata),
                **dict(metadata or {}),
                "case_id": case.case_id,
                "proposal_id": proposal.proposal_id,
                "decision_mode": proposal.decision.mode,
                "case_path": case_path,
            },
        )
        outcome_result = self._store_outcome(outcome)
        return LabPromotionResult(
            case_id=case.case_id,
            decision_mode=proposal.decision.mode,
            proposal_id=proposal.proposal_id,
            candidate_ref=None,
            promotion_submission=None,
            outcome_id=outcome.outcome_id,
            status="ignored",
            case_path=case_path,
            outcome_path=outcome_result["outcome_path"],
            metadata={
                **dict(case.metadata),
                **dict(metadata or {}),
                "case_path": case_path,
                "outcome_path": outcome_result["outcome_path"],
            },
        )

    def promote_feedback(
        self,
        feedback: Any,
        *,
        artifact_refs: tuple[str, ...] | list[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
        target_skill_name: str | None = None,
        owner: str = "agent-skill-platform",
        target_user: str = "platform engineer",
        recurring_job: str | None = None,
        source_kind: str = "case-proposal",
    ) -> LabPromotionResult:
        normalized_feedback = _coerce_feedback(feedback)
        metadata_map = dict(metadata or {})
        case = self.case_analyzer.analyze(
            normalized_feedback,
            artifact_refs=artifact_refs,
            metadata=metadata_map,
        )
        case_result = self._store_case(case)
        proposal = self.decider.decide(
            case,
            target_skill_name=target_skill_name,
            metadata=metadata_map,
        )
        case_path = case_result["case_path"]
        if proposal.decision.mode == "ignore":
            return self._ignored_flow(case=case, proposal=proposal, case_path=case_path, metadata=metadata_map)

        try:
            return self._positive_flow(
                case=case,
                proposal=proposal,
                case_path=case_path,
                decision_mode=proposal.decision.mode,
                metadata=metadata_map,
                owner=owner,
                target_user=target_user,
                recurring_job=recurring_job,
                source_kind=source_kind,
            )
        except Exception as exc:
            failure_outcome = OutcomeRecord(
                outcome_id=str(metadata_map.get("outcome_id") or f"outcome-{case.case_id}-{proposal.proposal_id}"),
                case_id=case.case_id,
                proposal_id=proposal.proposal_id,
                status="failed",
                summary=str(exc),
                result_ref=case_path,
                metadata={
                    **dict(case.metadata),
                    **metadata_map,
                    "case_id": case.case_id,
                    "proposal_id": proposal.proposal_id,
                    "decision_mode": proposal.decision.mode,
                    "case_path": case_path,
                    "error": str(exc),
                },
            )
            outcome_result = self._store_outcome(failure_outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=proposal.decision.mode,
                proposal_id=proposal.proposal_id,
                candidate_ref=metadata_map.get("candidate_ref"),
                promotion_submission=metadata_map.get("promotion_submission"),
                outcome_id=failure_outcome.outcome_id,
                status="failed",
                case_path=case_path,
                outcome_path=outcome_result["outcome_path"],
                error=str(exc),
                metadata={
                    **dict(case.metadata),
                    **metadata_map,
                    "case_path": case_path,
                    "outcome_path": outcome_result["outcome_path"],
                    "error": str(exc),
                },
            )

    def run(self, *args: Any, **kwargs: Any) -> LabPromotionResult:
        return self.promote_feedback(*args, **kwargs)


def orchestrate_lab_promotion(
    feedback: Any,
    *,
    backend_root: str | Path | None = None,
    registry_root: str | Path | None = None,
    registry_service: Any | None = None,
    artifact_refs: tuple[str, ...] | list[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    target_skill_name: str | None = None,
    owner: str = "agent-skill-platform",
    target_user: str = "platform engineer",
    recurring_job: str | None = None,
    source_kind: str = "case-proposal",
) -> LabPromotionResult:
    return LabPromotionOrchestrator(
        backend_root=backend_root,
        registry_root=registry_root,
        registry_service=registry_service,
    ).promote_feedback(
        feedback,
        artifact_refs=artifact_refs,
        metadata=metadata,
        target_skill_name=target_skill_name,
        owner=owner,
        target_user=target_user,
        recurring_job=recurring_job,
        source_kind=source_kind,
    )
