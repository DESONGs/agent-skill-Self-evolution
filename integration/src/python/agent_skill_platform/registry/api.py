from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..bootstrap import ensure_source_layout
from .service import LocalDevRegistryService

ensure_source_layout()

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..models import PromotionSubmission


class PublishRequest(BaseModel):
    source: str = Field(description="Package root directory or bundle zip path")


class FeedbackEnvelopeModel(BaseModel):
    run_id: str
    mode: str
    skill_id: str
    version_id: str | None = None
    action_id: str
    success: bool
    latency_ms: int = 0
    token_usage: dict[str, Any] = Field(default_factory=dict)
    artifact_count: int = 0
    error_code: str | None = None
    layer_source: str = "active"
    feedback_source: str = "RUNTIME"
    feedback_type: str = "EXECUTION"
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_registry_app(root: str | Path) -> FastAPI:
    service = LocalDevRegistryService(root)
    app = FastAPI(title="Agent Skill Platform Registry", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/skills")
    def list_skills() -> list[dict[str, Any]]:
        return service.list_skills()

    @app.get("/skills/{skill_id}")
    def get_skill(skill_id: str) -> dict[str, Any]:
        return service.get_skill(skill_id)

    @app.post("/publish")
    def publish(request: PublishRequest) -> dict[str, Any]:
        return service.publish_package(request.source)

    @app.get("/skills/{skill_id}/install-bundle")
    def resolve_bundle(skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        return service.resolve_install_bundle(skill_id, version_id=version_id)

    @app.post("/feedback")
    def ingest_feedback(request: FeedbackEnvelopeModel) -> dict[str, Any]:
        envelope = RunFeedbackEnvelope.from_dict(request.model_dump())
        return service.ingest_feedback(envelope)

    @app.post("/promotions")
    def submit_promotion(request: dict[str, Any]) -> dict[str, Any]:
        submission = PromotionSubmission(**request)
        return service.submit_promotion(submission)

    return app
