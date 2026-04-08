from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..models import CaseRecord
from ..paths import detect_platform_paths


def default_backend_root() -> Path:
    return detect_platform_paths().data_root / "backend_enhancement"


class CaseStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else default_backend_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cases_root = self.root / "cases"
        self.cases_root.mkdir(parents=True, exist_ok=True)

    def _case_path(self, case_id: str) -> Path:
        return self.cases_root / f"{case_id}.json"

    def save_case(self, case: CaseRecord) -> Path:
        path = self._case_path(case.case_id)
        path.write_text(json.dumps(case.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_case(self, case_id: str) -> CaseRecord:
        path = self._case_path(case_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Case file must contain an object: {path}")
        return CaseRecord.from_dict(payload)

    def list_cases(self) -> list[CaseRecord]:
        records: list[CaseRecord] = []
        for path in sorted(self.cases_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(CaseRecord.from_dict(payload))
        return records

    def record_case(self, case: CaseRecord) -> dict[str, Any]:
        path = self.save_case(case)
        return {"ok": True, "case_path": str(path), "case": case.to_dict()}

    def record_feedback(
        self,
        feedback: Any,
        *,
        artifact_refs: Iterable[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        case = CaseRecord.from_feedback(feedback, artifact_refs=tuple(artifact_refs or ()), metadata=metadata)
        return self.record_case(case)


def save_case_record(case: CaseRecord, *, root: str | Path | None = None) -> dict[str, Any]:
    return CaseStore(root).record_case(case)


def load_case_record(case_id: str, *, root: str | Path | None = None) -> CaseRecord:
    return CaseStore(root).load_case(case_id)


def list_case_records(*, root: str | Path | None = None) -> list[CaseRecord]:
    return CaseStore(root).list_cases()

