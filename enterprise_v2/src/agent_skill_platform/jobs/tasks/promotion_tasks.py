from __future__ import annotations

from ...models import PromotionSubmission
from ...services.container import get_service_container


def handle_promotion_job(*, job_id: str, payload: dict) -> dict:
    container = get_service_container()
    container.job_repository.mark_started(job_id)
    try:
        result = container.promotion_service.submit(PromotionSubmission.from_dict(payload))
        container.job_repository.mark_finished(job_id, result=result)
        return result
    except Exception as exc:
        container.job_repository.mark_failed(job_id, str(exc))
        raise
