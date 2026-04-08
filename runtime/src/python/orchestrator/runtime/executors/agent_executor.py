from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from ..execution import extract_json_object
from ..profiles import SkillExecutionProfile, profile_for_skill_type
from ..prompts import build_action_selection_prompt
from ..resolve import ResolvedAction
from ..runners import ActionResult, RunnerExecutionError, RunnerRegistry

try:  # pragma: no cover - optional dependency in test environments
    from ..client import SkillClient
except ModuleNotFoundError:  # pragma: no cover - allow tests to monkeypatch the client
    SkillClient = None  # type: ignore[assignment]


def _resolve_within(base: Path, candidate: Path) -> Path:
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise RunnerExecutionError(f"Path escapes the allowed workspace: {candidate}") from exc
    return resolved_candidate


def _catalog_item_action_id(item: Mapping[str, Any]) -> str:
    return str(item.get("action_id", "")).strip()


def _catalog_item_skill_id(item: Mapping[str, Any]) -> str:
    return str(item.get("skill_id", "")).strip()


def _catalog_item_runner_config(item: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(item.get("kind", "")).strip().lower()
    if kind == "mcp" and isinstance(item.get("mcp"), Mapping):
        return dict(item["mcp"])
    if kind == "subagent" and isinstance(item.get("subagent"), Mapping):
        return dict(item["subagent"])
    return {}


def _catalog_item_spec(item: Mapping[str, Any]) -> Any:
    from ..actions import ActionSpec

    payload = dict(item)
    payload.setdefault("id", payload.get("action_id"))
    return ActionSpec.from_dict(payload)


class AgentExecutor:
    def __init__(
        self,
        runner_registry: RunnerRegistry | None = None,
        *,
        profile: SkillExecutionProfile | None = None,
    ):
        self.runner_registry = runner_registry or RunnerRegistry()
        self.profile = profile or profile_for_skill_type("agent")

    @property
    def max_steps(self) -> int:
        return max(1, int(self.profile.policy.get("max_steps") or (3 if self.profile.skill_type == "ai_decision" else 6)))

    def read_file(
        self,
        path: str | Path,
        *,
        action: ResolvedAction,
        workspace_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        base_root = Path(workspace_dir).resolve() if workspace_dir is not None else (
            action.mounted_path or action.package_root or action.install_root
        )
        if base_root is None:
            raise RunnerExecutionError("AgentExecutor.read_file requires a workspace or install root")
        candidate = Path(path)
        target = candidate if candidate.is_absolute() else base_root / candidate
        resolved_target = _resolve_within(Path(base_root), target)
        return {
            "path": str(resolved_target),
            "content": resolved_target.read_text(encoding="utf-8"),
        }

    def _catalog(self, action: ResolvedAction) -> list[dict[str, Any]]:
        catalog = [dict(item) for item in action.action_catalog]
        if not catalog:
            catalog = [
                {
                    "skill_id": action.skill_id,
                    "version_id": action.version_id,
                    "action_id": action.action_id,
                    "kind": action.kind.value,
                    "description": action.description,
                    "default": action.is_default,
                    "entry": action.entry,
                    "runtime": action.runtime,
                    "timeout_sec": action.spec.timeout_sec if action.spec is not None else None,
                    "input_schema": dict(action.input_schema),
                    "output_schema": dict(action.output_schema),
                    "side_effects": list(action.side_effects),
                    "idempotency": action.idempotency,
                    "sandbox": action.sandbox,
                    "allow_network": action.allow_network,
                }
            ]
        return catalog

    def _resolve_catalog_action(self, base_action: ResolvedAction, action_id: str) -> ResolvedAction:
        catalog = self._catalog(base_action)
        item = next((candidate for candidate in catalog if _catalog_item_action_id(candidate) == action_id), None)
        if item is None:
            raise RunnerExecutionError(
                f"Action {action_id!r} is not declared for install {base_action.install_id!r}"
            )
        if _catalog_item_skill_id(item) and _catalog_item_skill_id(item) != base_action.skill_id:
            raise RunnerExecutionError(
                f"Action {action_id!r} belongs to skill {_catalog_item_skill_id(item)!r}, not {base_action.skill_id!r}"
            )

        spec = _catalog_item_spec(item)
        runner_config = _catalog_item_runner_config(item)
        return replace(
            base_action,
            action_id=spec.id,
            kind=spec.kind,
            runner_name=spec.kind.value,
            entry=spec.entry,
            runtime=spec.runtime,
            sandbox=spec.sandbox,
            allow_network=bool(spec.allow_network),
            input_schema=dict(spec.input_schema),
            output_schema=dict(spec.output_schema),
            side_effects=tuple(spec.side_effects),
            idempotency=spec.idempotency,
            description=spec.description,
            runner_config=runner_config,
            metadata={**dict(base_action.metadata), "skill_type": base_action.skill_type},
            is_default=bool(item.get("default", False)),
            spec=spec,
            action_catalog=base_action.action_catalog,
        )

    async def run_action(
        self,
        action_id: str,
        params: Any,
        *,
        action: ResolvedAction,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        resolved_action = self._resolve_catalog_action(action, action_id)
        return await self.runner_registry.run(resolved_action, params, workspace_dir=workspace_dir, env=env)

    def _decorate_result(
        self,
        result: ActionResult,
        *,
        action: ResolvedAction,
        planner_used: bool,
        planner_steps: int,
        planner_trace: list[dict[str, Any]],
    ) -> ActionResult:
        metadata = dict(result.metadata)
        metadata.update(
            {
                "skill_type": action.skill_type,
                "executor": self.profile.executor_name,
                "profile": self.profile.to_dict(),
                "tool_surface": list(self.profile.allowed_tools),
                "allowed_tools": list(self.profile.allowed_tools),
                "planner_used": planner_used,
                "planner_steps": planner_steps,
                "planner_trace": list(planner_trace),
            }
        )
        return replace(result, metadata=metadata)

    def _task_prompt_text(self, action: ResolvedAction, action_input: Any) -> str:
        fragments: list[str] = []
        if action.description.strip():
            fragments.append(action.description.strip())
        if isinstance(action_input, Mapping):
            for key in ("task", "prompt", "instruction", "goal", "description"):
                value = action_input.get(key)
                if isinstance(value, str) and value.strip():
                    fragments.append(value.strip())
            if not fragments:
                fragments.append(json.dumps(dict(action_input), ensure_ascii=False, sort_keys=True))
        elif action_input not in (None, ""):
            fragments.append(str(action_input))
        return "\n".join(fragment for fragment in fragments if fragment).strip() or action.action_id

    def _planner_client_kwargs(self, action: ResolvedAction, workspace_dir: Path | None) -> dict[str, Any]:
        return {
            "session_id": f"runtime-planner-{action.skill_id}-{action.action_id}",
            "allowed_tools": [],
            "disallowed_tools": ["Skill"],
            "cwd": str(workspace_dir) if workspace_dir is not None else None,
            "model": "sonnet",
        }

    async def _select_next_action(
        self,
        *,
        client: SkillClient,
        action: ResolvedAction,
        action_input: Any,
        prior_steps: list[ActionResult],
        workspace_dir: Path,
    ) -> dict[str, Any]:
        prompt = build_action_selection_prompt(
            task=self._task_prompt_text(action, action_input),
            action_catalog=self._catalog(action),
            working_dir=str(workspace_dir),
            output_dir=str(workspace_dir),
            prior_steps=[item.to_dict() for item in prior_steps],
            max_steps=self.max_steps,
        )
        response_text = await client.execute(prompt)

        payload = extract_json_object(response_text)
        if not isinstance(payload, dict):
            raise RunnerExecutionError("Planner did not return a valid JSON action selection")
        return payload

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        workspace_path = Path(workspace_dir).resolve() if workspace_dir is not None else (
            action.mounted_path or action.package_root or action.install_root
        )
        if workspace_path is None:
            raise RunnerExecutionError("AgentExecutor.run requires a workspace or install root")
        workspace_path = Path(workspace_path).resolve()

        catalog = self._catalog(action)
        planner_used = len(catalog) > 1
        planner_trace: list[dict[str, Any]] = []
        executed_results: list[ActionResult] = []
        executed_steps = 0
        current_result: ActionResult | None = None
        terminated_by_finish = False

        try:
            current_action = action
            current_result = await self.run_action(
                current_action.action_id,
                action_input,
                action=current_action,
                workspace_dir=workspace_path,
                env=env,
            )
            executed_steps += 1
            executed_results.append(current_result)
            planner_trace.append(
                {
                    "step": executed_steps,
                    "decision": {
                        "status": "select",
                        "skill_id": current_action.skill_id,
                        "action_id": current_action.action_id,
                        "summary": "initial action",
                    },
                    "result": current_result.to_dict(),
                }
            )
            if not current_result.is_success or not planner_used:
                return self._decorate_result(
                    current_result,
                    action=action,
                    planner_used=planner_used,
                    planner_steps=executed_steps,
                    planner_trace=planner_trace,
                )

            planner_client_cls = SkillClient
            if planner_client_cls is None:
                raise RunnerExecutionError("Planner client dependency is unavailable")

            async with planner_client_cls(**self._planner_client_kwargs(action, workspace_path)) as client:
                while executed_steps < self.max_steps:
                    decision = await self._select_next_action(
                        client=client,
                        action=action,
                        action_input=action_input,
                        prior_steps=list(executed_results),
                        workspace_dir=workspace_path,
                    )
                    status = str(decision.get("status") or "").strip().lower()
                    if status == "finish":
                        planner_trace.append(
                            {
                                "step": executed_steps + 1,
                                "decision": decision,
                                "result": None,
                            }
                        )
                        terminated_by_finish = True
                        break

                    next_action_id = str(decision.get("action_id") or "").strip()
                    next_skill_id = str(decision.get("skill_id") or "").strip()
                    next_input = decision.get("input") or {}
                    if not isinstance(next_input, dict):
                        next_input = {}
                    if not next_action_id:
                        raise RunnerExecutionError("Planner selection is missing an action_id")
                    if next_skill_id and next_skill_id != action.skill_id:
                        raise RunnerExecutionError(
                            f"Planner selected skill {next_skill_id!r}, but the installed skill is {action.skill_id!r}"
                        )

                    selected_action = self._resolve_catalog_action(action, next_action_id)
                    current_result = await self.run_action(
                        selected_action.action_id,
                        next_input,
                        action=selected_action,
                        workspace_dir=workspace_path,
                        env=env,
                    )
                    executed_steps += 1
                    executed_results.append(current_result)
                    planner_trace.append(
                        {
                            "step": executed_steps,
                            "decision": decision,
                            "result": current_result.to_dict(),
                        }
                    )
                    if not current_result.is_success:
                        break
                else:
                    if current_result is None:
                        raise RunnerExecutionError("Planner did not execute any action")

            if (
                executed_steps >= self.max_steps
                and planner_used
                and not terminated_by_finish
                and current_result is not None
                and current_result.is_success
            ):
                limit_result = current_result or ActionResult.failure(
                    action_id=action.action_id,
                    skill_id=action.skill_id,
                    runner_name=action.runner_name,
                    error=f"Planner exceeded max steps ({self.max_steps})",
                    error_code="step_limit_exceeded",
                )
                return self._decorate_result(
                    replace(
                        limit_result,
                        status="failed",
                        error=f"Planner exceeded max steps ({self.max_steps})",
                        error_code="step_limit_exceeded",
                    ),
                    action=action,
                    planner_used=planner_used,
                    planner_steps=executed_steps,
                    planner_trace=planner_trace,
                )

            if current_result is None:
                raise RunnerExecutionError("Planner did not produce a result")
            return self._decorate_result(
                current_result,
                action=action,
                planner_used=planner_used,
                planner_steps=executed_steps,
                planner_trace=planner_trace,
            )
        except RunnerExecutionError as exc:
            fallback = current_result or ActionResult.failure(
                action_id=action.action_id,
                skill_id=action.skill_id,
                runner_name=action.runner_name,
                error=str(exc),
                error_code="planner_error",
            )
            return self._decorate_result(
                replace(
                    fallback,
                    status="failed",
                    error=str(exc),
                    error_code=getattr(fallback, "error_code", None) or "planner_error",
                ),
                action=action,
                planner_used=planner_used,
                planner_steps=executed_steps,
                planner_trace=planner_trace,
            )
