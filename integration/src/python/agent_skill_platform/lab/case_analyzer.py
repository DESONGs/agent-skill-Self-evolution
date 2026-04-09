from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..models import CaseRecord
from .case_store import CaseStore


class CaseAnalyzer:
    def analyze(
        self,
        feedback: Any,
        *,
        artifact_refs: Iterable[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CaseRecord:
        return CaseRecord.from_feedback(feedback, artifact_refs=tuple(artifact_refs or ()), metadata=metadata)

    def analyze_and_store(
        self,
        feedback: Any,
        *,
        store: CaseStore | None = None,
        artifact_refs: Iterable[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_store = store or CaseStore()
        case = self.analyze(feedback, artifact_refs=artifact_refs, metadata=metadata)
        return resolved_store.record_case(case)


def analyze_feedback_case(
    feedback: Any,
    *,
    artifact_refs: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CaseRecord:
    return CaseAnalyzer().analyze(feedback, artifact_refs=artifact_refs, metadata=metadata)

