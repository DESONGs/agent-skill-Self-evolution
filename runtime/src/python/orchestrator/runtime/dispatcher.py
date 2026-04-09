from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .executors import AgentExecutor, ScriptExecutor
from .profiles import SkillType, normalize_skill_type, profile_for_skill_type
from .runners import ActionResult, RunnerRegistry
from .resolve import ResolvedAction


class SkillRuntimeDispatcher:
    def __init__(self, runner_registry: RunnerRegistry | None = None):
        self.runner_registry = runner_registry or RunnerRegistry()
        self.script_executor = ScriptExecutor(self.runner_registry)

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        skill_type = normalize_skill_type(getattr(action, "skill_type", None))
        if skill_type == SkillType.SCRIPT.value:
            result = await self.script_executor.run(
                action,
                action_input,
                workspace_dir=workspace_dir,
                env=env,
            )
        else:
            agent_executor = AgentExecutor(self.runner_registry, profile=profile_for_skill_type(skill_type))
            result = await agent_executor.run(
                action,
                action_input,
                workspace_dir=workspace_dir,
                env=env,
            )
        return result
