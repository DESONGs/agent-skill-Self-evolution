from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..lab.case_analyzer import CaseAnalyzer
from ..lab.decider import Decider
from ..lab.proposal_adapter import ProposalAdapter
from ..models import CandidateProposal, LabPromotionResult, OutcomeRecord, PromotionSubmission
from ..storage.object_store.client import ObjectStoreClient
from ..storage.repositories.lab_repository import LabRepository
from .registry_service import EnterpriseRegistryService


def _coerce_feedback(feedback: Any) -> RunFeedbackEnvelope:
    if isinstance(feedback, RunFeedbackEnvelope):
        return feedback
    if hasattr(feedback, "to_dict"):
        return RunFeedbackEnvelope.from_dict(feedback.to_dict())
    return RunFeedbackEnvelope.from_dict(dict(feedback))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LabPromotionOrchestrator:
    def __init__(
        self,
        *,
        lab_repository: LabRepository,
        registry_service: EnterpriseRegistryService,
        object_store: ObjectStoreClient,
        case_analyzer: CaseAnalyzer | None = None,
        decider: Decider | None = None,
        proposal_adapter: ProposalAdapter | None = None,
    ):
        self.lab_repository = lab_repository
        self.registry_service = registry_service
        self.object_store = object_store
        self.case_analyzer = case_analyzer or CaseAnalyzer()
        self.decider = decider or Decider()
        self.proposal_adapter = proposal_adapter or ProposalAdapter()

    def submit(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        return self.registry_service.submit_promotion(submission)

    def process_feedback(
        self,
        feedback: RunFeedbackEnvelope | dict[str, Any],
        *,
        artifact_refs: tuple[str, ...] | list[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LabPromotionResult:
        normalized_feedback = _coerce_feedback(feedback)
        case = self.case_analyzer.analyze(normalized_feedback, artifact_refs=artifact_refs, metadata=metadata)
        self.lab_repository.store_case(case)

        proposal = self.decider.decide(case, target_skill_name=case.source.skill_id, metadata=metadata)
        decision_mode = proposal.decision.mode
        if decision_mode == "ignore":
            outcome = OutcomeRecord(
                outcome_id=f"outcome-{case.case_id}",
                case_id=case.case_id,
                proposal_id=None,
                status="ignored",
                summary=proposal.decision.reason,
                result_ref=None,
                metadata={**dict(metadata or {}), "decision_mode": decision_mode},
            )
            self.lab_repository.store_outcome(outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=decision_mode,
                proposal_id=None,
                candidate_ref=None,
                promotion_submission=None,
                outcome_id=outcome.outcome_id,
                status="ignored",
                metadata=outcome.metadata,
            )

        candidate_dir = Path(tempfile.mkdtemp(prefix="asp-enterprise-candidate-"))
        candidate_path = self.proposal_adapter.write_candidate_file(proposal, candidate_dir / "candidate.yaml")
        candidate_ref = self.object_store.upload_file(
            candidate_path,
            key=f"candidates/{case.case_id}/{proposal.proposal_id}/candidate.yaml",
            content_type="application/x-yaml",
        )
        self.lab_repository.store_proposal(proposal, candidate_ref=candidate_ref)
        candidate_payload = self.proposal_adapter.to_candidate_payload(proposal)
        candidate_sha = _sha256_file(candidate_path)
        submission = PromotionSubmission(
            candidate_id=str(candidate_payload["candidate"]["id"]),
            candidate_slug=str(candidate_payload["candidate"]["slug"]),
            run_id=case.source.run_id,
            bundle_path=candidate_ref,
            bundle_sha256=candidate_sha,
            manifest=candidate_payload,
            evaluation_summary={
                "case_id": case.case_id,
                "decision_mode": decision_mode,
                "decision_reason": proposal.decision.reason,
                "target_layer": proposal.target_layer,
                "change_summary": proposal.change_summary,
            },
            promotion_decision=decision_mode,
            recommended_rollout_strategy="manual_review",
            lineage={
                "case_id": case.case_id,
                "proposal_id": proposal.proposal_id,
                "decision_mode": decision_mode,
            },
            metadata={
                **dict(metadata or {}),
                "candidate_ref": candidate_ref,
                "case_id": case.case_id,
                "proposal_id": proposal.proposal_id,
                "decision_mode": decision_mode,
            },
        )
        try:
            promotion_submission = self.registry_service.submit_promotion(submission)
            outcome = OutcomeRecord(
                outcome_id=f"outcome-{case.case_id}-{proposal.proposal_id}",
                case_id=case.case_id,
                proposal_id=proposal.proposal_id,
                status="promoted",
                summary=proposal.change_summary or proposal.decision.reason,
                result_ref=promotion_submission.get("submission_path"),
                metadata={**dict(metadata or {}), "candidate_ref": candidate_ref, "decision_mode": decision_mode},
            )
            self.lab_repository.store_outcome(outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=decision_mode,
                proposal_id=proposal.proposal_id,
                candidate_ref=candidate_ref,
                promotion_submission=promotion_submission,
                outcome_id=outcome.outcome_id,
                status="promoted",
                metadata=outcome.metadata,
            )
        except Exception as exc:
            outcome = OutcomeRecord(
                outcome_id=f"outcome-{case.case_id}-{proposal.proposal_id}",
                case_id=case.case_id,
                proposal_id=proposal.proposal_id,
                status="failed",
                summary=str(exc),
                result_ref=candidate_ref,
                metadata={**dict(metadata or {}), "candidate_ref": candidate_ref, "decision_mode": decision_mode, "error": str(exc)},
            )
            self.lab_repository.store_outcome(outcome)
            return LabPromotionResult(
                case_id=case.case_id,
                decision_mode=decision_mode,
                proposal_id=proposal.proposal_id,
                candidate_ref=candidate_ref,
                promotion_submission=None,
                outcome_id=outcome.outcome_id,
                status="failed",
                error=str(exc),
                metadata=outcome.metadata,
            )
        finally:
            shutil.rmtree(candidate_dir, ignore_errors=True)
