from __future__ import annotations

from typing import Any, Mapping

from ..models import CandidateProposal, CaseRecord, EvolutionDecision


class Decider:
    def decide(
        self,
        case: CaseRecord,
        *,
        target_skill_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CandidateProposal:
        decision = EvolutionDecision.patch_first(case)
        merged_metadata = {**case.metadata, **dict(metadata or {}), **decision.metadata}
        return CandidateProposal.from_case(
            case,
            decision=decision,
            target_skill_name=target_skill_name,
            metadata=merged_metadata,
        )


def decide_case_evolution(
    case: CaseRecord,
    *,
    target_skill_name: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CandidateProposal:
    return Decider().decide(case, target_skill_name=target_skill_name, metadata=metadata)

