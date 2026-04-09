from __future__ import annotations

from ..queue import QueueManager  # noqa: F401
from ...services.container import get_service_container


def handle_feedback_job(*, job_id: str, payload: dict) -> dict:
    container = get_service_container()
    container.job_repository.mark_started(job_id)
    try:
        result = container.promotion_service.process_feedback(payload).to_dict()
        container.job_repository.mark_finished(job_id, result=result)
        return result
    except Exception as exc:
        container.job_repository.mark_failed(job_id, str(exc))
        raise
