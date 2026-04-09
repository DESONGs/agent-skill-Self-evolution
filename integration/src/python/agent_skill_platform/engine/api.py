from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .models import ExecuteSkillRequest, FindSkillRequest
from .service import EngineService, open_engine


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


def create_engine_app(root: str | Path | None = None) -> FastAPI:
    service = open_engine(root)
    app = FastAPI(title="Agent Skill Platform Engine", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/find-skill")
    def find_skill(request: FindSkillRequestModel) -> dict[str, Any]:
        return service.find_skill(_to_find_request(request)).to_dict()

    @app.post("/execute-skill")
    def execute_skill(request: ExecuteSkillRequestModel) -> dict[str, Any]:
        try:
            return service.execute_skill(_to_execute_request(request)).to_dict()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def register_engine_routes(app: FastAPI, service: EngineService) -> None:
    @app.post("/find-skill")
    def find_skill(request: FindSkillRequestModel) -> dict[str, Any]:
        return service.find_skill(_to_find_request(request)).to_dict()

    @app.post("/execute-skill")
    def execute_skill(request: ExecuteSkillRequestModel) -> dict[str, Any]:
        try:
            return service.execute_skill(_to_execute_request(request)).to_dict()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
