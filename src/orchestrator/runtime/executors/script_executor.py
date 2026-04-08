from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from ..profiles import profile_for_skill_type
from ..resolve import ResolvedAction
from ..runners import ActionResult, RunnerRegistry


class ScriptExecutor:
    def __init__(self, runner_registry: RunnerRegistry | None = None):
        self.runner_registry = runner_registry or RunnerRegistry()
        self.profile = profile_for_skill_type("script")

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Any = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        result = await self.runner_registry.run(action, action_input, workspace_dir=workspace_dir, env=env)
        metadata = dict(result.metadata)
        metadata.setdefault("skill_type", action.skill_type)
        metadata.setdefault("executor", self.profile.executor_name)
        metadata.setdefault("profile", self.profile.to_dict())
        metadata.setdefault("tool_surface", list(self.profile.allowed_tools))
        metadata.setdefault("allowed_tools", list(self.profile.allowed_tools))
        return replace(result, metadata=metadata)
