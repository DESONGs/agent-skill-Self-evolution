from __future__ import annotations

from typing import Any

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..jobs.queue import QueueManager
from .registry_service import EnterpriseRegistryService


class FeedbackService:
    def __init__(self, registry_service: EnterpriseRegistryService, queue_manager: QueueManager):
        self.registry_service = registry_service
        self.queue_manager = queue_manager

    def ingest(self, envelope: RunFeedbackEnvelope | dict[str, Any]) -> dict[str, Any]:
        response = self.registry_service.ingest_feedback(envelope)
        feedback_payload = dict(response["feedback"])
        queued = self.queue_manager.enqueue(
            job_type="feedback",
            queue_name=self.queue_manager.settings.feedback_queue,
            task_path="agent_skill_platform.jobs.tasks.feedback_tasks.handle_feedback_job",
            payload=feedback_payload,
        )
        response["job_id"] = queued.job_id
        return response
