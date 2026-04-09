from __future__ import annotations

from ...services.container import get_service_container


def rebuild_projection_job(*, job_id: str, payload: dict) -> dict:
    container = get_service_container()
    container.job_repository.mark_started(job_id)
    try:
        projection = container.registry_service.get_skill_projection(
            str(payload.get("skill_id", "")),
            version_id=payload.get("version_id"),
        )
        result = {"ok": True, "projection": projection}
        container.job_repository.mark_finished(job_id, result=result)
        return result
    except Exception as exc:
        container.job_repository.mark_failed(job_id, str(exc))
        raise
