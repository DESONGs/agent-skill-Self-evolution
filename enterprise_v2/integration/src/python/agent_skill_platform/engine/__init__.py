from __future__ import annotations

from typing import Any

from .models import (
    ExecuteSkillRequest,
    ExecuteSkillResponse,
    FindSkillRequest,
    FindSkillResponse,
    RuntimeExecutionResponse,
    SkillProjection,
)
from .search import EngineSearchService
from .service import EngineService, execute_skill, find_skill, open_engine


def build_engine_app(root: str | Any = None) -> Any:
    from .api import create_engine_app

    return create_engine_app(root)


def register_engine_routes(app: Any, service: EngineService) -> None:
    from .api import register_engine_routes as _register_engine_routes

    _register_engine_routes(app, service)


__all__ = [
    "EngineSearchService",
    "EngineService",
    "ExecuteSkillRequest",
    "ExecuteSkillResponse",
    "FindSkillRequest",
    "FindSkillResponse",
    "RuntimeExecutionResponse",
    "SkillProjection",
    "build_engine_app",
    "execute_skill",
    "find_skill",
    "open_engine",
    "register_engine_routes",
]
