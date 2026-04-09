from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import sessionmaker

from ..postgres.models import JobRunRecord
from ..postgres.session import session_scope


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRepository:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def create_job(self, *, job_id: str, job_type: str, queue_name: str, payload: dict[str, Any], status: str = "queued") -> None:
        with session_scope(self.session_factory) as session:
            session.merge(
                JobRunRecord(
                    job_id=job_id,
                    job_type=job_type,
                    queue_name=queue_name,
                    status=status,
                    payload_json=payload,
                    result_json=None,
                    error_text=None,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )

    def mark_started(self, job_id: str) -> None:
        with session_scope(self.session_factory) as session:
            row = session.get(JobRunRecord, job_id)
            if row is None:
                return
            row.status = "started"
            row.updated_at = _utc_now()

    def mark_finished(self, job_id: str, *, result: dict[str, Any] | None = None, status: str = "completed") -> None:
        with session_scope(self.session_factory) as session:
            row = session.get(JobRunRecord, job_id)
            if row is None:
                return
            row.status = status
            row.result_json = result
            row.updated_at = _utc_now()

    def mark_failed(self, job_id: str, error_text: str) -> None:
        with session_scope(self.session_factory) as session:
            row = session.get(JobRunRecord, job_id)
            if row is None:
                return
            row.status = "failed"
            row.error_text = error_text
            row.updated_at = _utc_now()

    def get_job(self, job_id: str) -> dict[str, Any]:
        with session_scope(self.session_factory) as session:
            row = session.get(JobRunRecord, job_id)
            if row is None:
                raise KeyError(f"Unknown job: {job_id}")
            return {
                "job_id": row.job_id,
                "job_type": row.job_type,
                "queue_name": row.queue_name,
                "status": row.status,
                "payload": dict(row.payload_json or {}),
                "result": dict(row.result_json or {}) if row.result_json else None,
                "error_text": row.error_text,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
