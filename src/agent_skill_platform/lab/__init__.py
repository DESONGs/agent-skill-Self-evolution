from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch_agent.cli.runtime import get_run_artifacts, get_run_status, init_project, run_project, validate_project

from ..models import (
    CandidateProposal,
    CaseRecord,
    EvolutionDecision,
    LabPromotionResult,
    OutcomeRecord,
    PromotionSubmission,
)
from .case_analyzer import CaseAnalyzer, analyze_feedback_case
from .case_store import CaseStore, default_backend_root, list_case_records, load_case_record, save_case_record
from .decider import Decider, decide_case_evolution
from .outcome_store import OutcomeStore, load_outcome_record, save_outcome_record
from .proposal_adapter import ProposalAdapter, adapt_proposal_to_candidate
from .promotion_orchestrator import LabPromotionOrchestrator, orchestrate_lab_promotion as _orchestrate_lab_promotion


def init_skill_lab_project(
    project_root: str | Path,
    *,
    project_name: str | None = None,
    pack_id: str = "skill_research",
    data_source: str = "datasets/input.json",
    overwrite: bool = False,
) -> dict[str, Any]:
    return init_project(
        Path(project_root),
        project_name=project_name,
        pack_id=pack_id,
        data_source=data_source,
        overwrite=overwrite,
    )


def validate_skill_lab_project(project_root: str | Path) -> dict[str, Any]:
    return validate_project(Path(project_root))


def run_skill_lab_project(project_root: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    return run_project(Path(project_root), run_id=run_id)


def get_skill_lab_run_status(project_root: str | Path, run_id: str) -> dict[str, Any]:
    return get_run_status(Path(project_root), run_id)


def get_skill_lab_run_artifacts(project_root: str | Path, run_id: str) -> list[dict[str, Any]]:
    return get_run_artifacts(Path(project_root), run_id)


def build_promotion_submission(
    project_root: str | Path,
    run_id: str,
    *,
    lineage: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PromotionSubmission:
    return PromotionSubmission.from_skill_lab_run(Path(project_root), run_id, lineage=lineage, metadata=metadata)


def build_promotion_submission_with_lineage(
    project_root: str | Path,
    run_id: str,
    *,
    lineage: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> PromotionSubmission:
    return build_promotion_submission(project_root, run_id, lineage=lineage, metadata=metadata)


def build_case_store(root: str | Path | None = None) -> CaseStore:
    return CaseStore(root)


def build_outcome_store(root: str | Path | None = None) -> OutcomeStore:
    return OutcomeStore(root)


def analyze_feedback(
    feedback: Any,
    *,
    artifact_refs: list[str] | tuple[str, ...] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CaseRecord:
    return analyze_feedback_case(feedback, artifact_refs=artifact_refs, metadata=metadata)


def analyze_feedback_and_store(
    feedback: Any,
    *,
    root: str | Path | None = None,
    artifact_refs: list[str] | tuple[str, ...] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return CaseAnalyzer().analyze_and_store(feedback, store=CaseStore(root), artifact_refs=artifact_refs, metadata=metadata)


def decide_evolution(
    case: CaseRecord,
    *,
    target_skill_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CandidateProposal:
    return decide_case_evolution(case, target_skill_name=target_skill_name, metadata=metadata)


def adapt_candidate_proposal(
    proposal: CandidateProposal,
    *,
    owner: str = "agent-skill-platform",
    target_user: str = "platform engineer",
    recurring_job: str | None = None,
    source_kind: str = "case-proposal",
) -> dict[str, Any]:
    return adapt_proposal_to_candidate(
        proposal,
        owner=owner,
        target_user=target_user,
        recurring_job=recurring_job,
        source_kind=source_kind,
    )


def build_lab_promotion_orchestrator(
    *,
    backend_root: str | Path | None = None,
    registry_root: str | Path | None = None,
    registry_service: Any | None = None,
) -> LabPromotionOrchestrator:
    return LabPromotionOrchestrator(
        backend_root=backend_root,
        registry_root=registry_root,
        registry_service=registry_service,
    )


def promote_feedback_to_lab(
    feedback: Any,
    *,
    backend_root: str | Path | None = None,
    registry_root: str | Path | None = None,
    registry_service: Any | None = None,
    artifact_refs: tuple[str, ...] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    target_skill_name: str | None = None,
    owner: str = "agent-skill-platform",
    target_user: str = "platform engineer",
    recurring_job: str | None = None,
    source_kind: str = "case-proposal",
) -> LabPromotionResult:
    return _orchestrate_lab_promotion(
        feedback,
        backend_root=backend_root,
        registry_root=registry_root,
        registry_service=registry_service,
        artifact_refs=artifact_refs,
        metadata=metadata,
        target_skill_name=target_skill_name,
        owner=owner,
        target_user=target_user,
        recurring_job=recurring_job,
        source_kind=source_kind,
    )


__all__ = [
    "adapt_candidate_proposal",
    "analyze_feedback",
    "analyze_feedback_and_store",
    "build_promotion_submission",
    "build_promotion_submission_with_lineage",
    "build_case_store",
    "build_outcome_store",
    "CaseAnalyzer",
    "CaseRecord",
    "CaseStore",
    "CandidateProposal",
    "Decider",
    "LabPromotionOrchestrator",
    "LabPromotionResult",
    "default_backend_root",
    "decide_evolution",
    "EvolutionDecision",
    "get_skill_lab_run_artifacts",
    "get_skill_lab_run_status",
    "init_skill_lab_project",
    "list_case_records",
    "load_case_record",
    "load_outcome_record",
    "OutcomeRecord",
    "OutcomeStore",
    "ProposalAdapter",
    "build_lab_promotion_orchestrator",
    "run_skill_lab_project",
    "promote_feedback_to_lab",
    "save_case_record",
    "save_outcome_record",
    "validate_skill_lab_project",
]
