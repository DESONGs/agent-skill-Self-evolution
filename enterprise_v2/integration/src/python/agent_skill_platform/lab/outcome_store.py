from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..models import OutcomeRecord
from ..paths import detect_platform_paths


def default_backend_root() -> Path:
    return detect_platform_paths().data_root / "backend_enhancement"


class OutcomeStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else default_backend_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.outcomes_root = self.root / "outcomes"
        self.outcomes_root.mkdir(parents=True, exist_ok=True)

    def _outcome_path(self, outcome_id: str) -> Path:
        return self.outcomes_root / f"{outcome_id}.json"

    def save_outcome(self, outcome: OutcomeRecord) -> Path:
        path = self._outcome_path(outcome.outcome_id)
        path.write_text(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_outcome(self, outcome_id: str) -> OutcomeRecord:
        path = self._outcome_path(outcome_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Outcome file must contain an object: {path}")
        return OutcomeRecord.from_dict(payload)

    def list_outcomes(self) -> list[OutcomeRecord]:
        records: list[OutcomeRecord] = []
        for path in sorted(self.outcomes_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(OutcomeRecord.from_dict(payload))
        return records

    def record_outcome(self, outcome: OutcomeRecord) -> dict[str, Any]:
        path = self.save_outcome(outcome)
        return {"ok": True, "outcome_path": str(path), "outcome": outcome.to_dict()}

    def record_case_outcome(
        self,
        *,
        case_id: str,
        proposal_id: str | None = None,
        status: str = "recorded",
        summary: str = "",
        result_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        outcome_id = str((metadata or {}).get("outcome_id") or f"outcome-{case_id}")
        outcome = OutcomeRecord(
            outcome_id=outcome_id,
            case_id=case_id,
            proposal_id=proposal_id,
            status=status,
            summary=summary,
            result_ref=result_ref,
            metadata=dict(metadata or {}),
        )
        return self.record_outcome(outcome)


def save_outcome_record(outcome: OutcomeRecord, *, root: str | Path | None = None) -> dict[str, Any]:
    return OutcomeStore(root).record_outcome(outcome)


def load_outcome_record(outcome_id: str, *, root: str | Path | None = None) -> OutcomeRecord:
    return OutcomeStore(root).load_outcome(outcome_id)

