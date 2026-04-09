from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from ...models import CandidateProposal, CaseRecord, OutcomeRecord
from ..postgres.models import CandidateProposalRecord, CaseRecordRow, OutcomeRecordRow
from ..postgres.session import session_scope


class LabRepository:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def store_case(self, case: CaseRecord) -> None:
        with session_scope(self.session_factory) as session:
            session.merge(
                CaseRecordRow(
                    case_id=case.case_id,
                    payload_json=case.to_dict(),
                    created_at=case.created_at,
                )
            )

    def store_proposal(self, proposal: CandidateProposal, *, candidate_ref: str | None = None) -> None:
        payload = proposal.to_dict()
        candidate_payload = payload.get("metadata", {})
        with session_scope(self.session_factory) as session:
            session.merge(
                CandidateProposalRecord(
                    proposal_id=proposal.proposal_id,
                    case_id=proposal.case_id,
                    candidate_id=str(candidate_payload.get("candidate_id") or "") or None,
                    candidate_slug=str(candidate_payload.get("candidate_slug") or "") or None,
                    payload_json=payload,
                    candidate_ref=candidate_ref,
                    created_at=proposal.created_at,
                )
            )

    def store_outcome(self, outcome: OutcomeRecord) -> None:
        with session_scope(self.session_factory) as session:
            session.merge(
                OutcomeRecordRow(
                    outcome_id=outcome.outcome_id,
                    case_id=outcome.case_id,
                    proposal_id=outcome.proposal_id,
                    status=outcome.status,
                    payload_json=outcome.to_dict(),
                    created_at=outcome.created_at,
                )
            )
