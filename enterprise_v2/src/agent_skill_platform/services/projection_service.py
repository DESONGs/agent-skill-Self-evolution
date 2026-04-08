from __future__ import annotations

from typing import Any

from ..engine.models import FindSkillResponse
from ..engine.search import EngineSearchService


class ProjectionService:
    def __init__(self, registry_service: Any):
        self.registry_service = registry_service
        self.search_service = EngineSearchService(registry_service)

    def find_skill(self, request: Any, **kwargs: Any) -> FindSkillResponse:
        return self.search_service.search(request, **kwargs)
