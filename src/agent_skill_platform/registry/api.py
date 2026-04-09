from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..engine.models import ExecuteSkillRequest, FindSkillRequest
from ..models import PromotionSubmission
from ..services.container import get_service_container
from ..storage.postgres.session import migrate_schema


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


class FindSkillFiltersModel(BaseModel):
    skill_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    owner: str | None = None
    risk_level: str | None = None
    official_only: bool | None = None
    skill_ids: list[str] = Field(default_factory=list)


class FindSkillRequestModel(BaseModel):
    query: str = ""
    limit: int = 5
    filters: FindSkillFiltersModel = Field(default_factory=FindSkillFiltersModel)


class ExecuteSkillRequestModel(BaseModel):
    skill_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    action_id: str | None = None
    version_id: str | None = None
    trace_id: str | None = None
    environment_profile: str | None = None
    workspace_dir: str | None = None
    run_id: str | None = None
    install_root: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    max_sandbox: str | None = None
    allow_network: bool = False


def _to_find_request(request: FindSkillRequestModel) -> FindSkillRequest:
    return FindSkillRequest(
        query=request.query,
        limit=request.limit,
        skill_type=request.filters.skill_type,
        tags=tuple(request.filters.tags),
        owner=request.filters.owner,
        risk_level=request.filters.risk_level,
        official_only=request.filters.official_only,
        skill_ids=tuple(request.filters.skill_ids),
    )


def _to_execute_request(request: ExecuteSkillRequestModel) -> ExecuteSkillRequest:
    return ExecuteSkillRequest(
        skill_id=request.skill_id,
        parameters=dict(request.parameters),
        action_id=request.action_id,
        version_id=request.version_id,
        trace_id=request.trace_id,
        environment_profile=request.environment_profile,
        workspace_dir=request.workspace_dir,
        run_id=request.run_id,
        install_root=request.install_root,
        env=dict(request.env),
        max_sandbox=request.max_sandbox,
        allow_network=request.allow_network,
    )


def _register_shared_engine_routes(app: FastAPI) -> None:
    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/find-skill")
    def find_skill(request: FindSkillRequestModel) -> dict[str, Any]:
        container = get_service_container()
        return container.projection_service.find_skill(_to_find_request(request)).to_dict()

    @app.post("/execute-skill")
    def execute_skill(request: ExecuteSkillRequestModel) -> dict[str, Any]:
        container = get_service_container()
        try:
            return container.execution_service.execute(_to_execute_request(request)).to_dict()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


def _storage_health_payload() -> tuple[bool, dict[str, Any]]:
    try:
        container = get_service_container()
        return True, container.object_store.healthcheck()
    except Exception as exc:
        return False, {"ok": False, "error": str(exc)}


def create_engine_app(root: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Agent Skill Platform Engine", version="0.2.0")

    @app.on_event("startup")
    def startup() -> None:
        migrate_schema()

    _register_shared_engine_routes(app)
    return app


def create_registry_app(root: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Agent Skill Platform Registry", version="0.2.0")

    @app.on_event("startup")
    def startup() -> None:
        migrate_schema()

    _register_shared_engine_routes(app)

    @app.get("/readyz")
    def readyz(response: Response) -> dict[str, Any]:
        storage_ok, storage = _storage_health_payload()
        if not storage_ok:
            response.status_code = 503
        return {"ok": storage_ok, "db": storage_ok, "storage": storage}

    @app.get("/internal/storage/health")
    def storage_health(response: Response) -> dict[str, Any]:
        storage_ok, storage = _storage_health_payload()
        if not storage_ok:
            response.status_code = 503
        return storage

    @app.get("/internal/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        container = get_service_container()
        try:
            return container.job_repository.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/skills")
    def list_skills() -> list[dict[str, Any]]:
        container = get_service_container()
        return container.registry_service.list_skills()

    @app.get("/skills/projections")
    def list_skill_projections() -> list[dict[str, Any]]:
        container = get_service_container()
        return container.registry_service.list_skill_projections()

    @app.get("/skills/{skill_id}/projection")
    def get_skill_projection(skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        container = get_service_container()
        try:
            return container.registry_service.get_skill_projection(skill_id, version_id=version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/skills/{skill_id}")
    def get_skill(skill_id: str) -> dict[str, Any]:
        container = get_service_container()
        try:
            return container.registry_service.get_skill(skill_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/publish")
    def publish(request: PublishRequest) -> dict[str, Any]:
        container = get_service_container()
        try:
            result = container.registry_service.publish_package(request.source)
            queued = container.queue_manager.enqueue(
                job_type="projection",
                queue_name=container.settings.projection_queue,
                task_path="agent_skill_platform.jobs.tasks.projection_tasks.rebuild_projection_job",
                payload={"skill_id": result["skill_id"], "version_id": result["version_id"]},
            )
            result["job_id"] = queued.job_id
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/skills/{skill_id}/install-bundle")
    def resolve_bundle(skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        container = get_service_container()
        try:
            return container.registry_service.resolve_install_bundle(skill_id, version_id=version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/feedback")
    def ingest_feedback(request: FeedbackEnvelopeModel) -> dict[str, Any]:
        container = get_service_container()
        envelope = RunFeedbackEnvelope.from_dict(request.model_dump())
        return container.feedback_service.ingest(envelope)

    @app.post("/promotions")
    def submit_promotion(request: dict[str, Any]) -> dict[str, Any]:
        container = get_service_container()
        submission = PromotionSubmission(**request)
        return container.promotion_service.submit(submission)

    return app


app = create_registry_app()


def main() -> None:
    import uvicorn

    settings = get_service_container().settings
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
