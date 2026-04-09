from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from redis import Redis
from rq import Queue

from ..config.settings import EnterpriseSettings
from ..storage.repositories.job_repository import JobRepository


@dataclass(frozen=True)
class EnqueuedJob:
    job_id: str
    queue_name: str


class QueueManager:
    def __init__(self, settings: EnterpriseSettings, job_repository: JobRepository):
        self.settings = settings
        self.job_repository = job_repository
        self.redis = Redis.from_url(settings.redis_url)

    def enqueue(self, *, job_type: str, queue_name: str, task_path: str, payload: dict[str, Any]) -> EnqueuedJob:
        job_id = f"{job_type}-{uuid.uuid4().hex[:12]}"
        self.job_repository.create_job(job_id=job_id, job_type=job_type, queue_name=queue_name, payload=payload)
        queue = Queue(name=queue_name, connection=self.redis)
        queue.enqueue(task_path, kwargs={"job_id": job_id, "payload": payload}, job_id=job_id)
        return EnqueuedJob(job_id=job_id, queue_name=queue_name)
