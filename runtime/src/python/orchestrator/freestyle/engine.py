"""Freestyle execution engine with bounded declared-action execution."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional

from config import get_config
from loguru import logger as _logger
from logging_config import add_file_sink, map_level
from orchestrator.base import EngineMeta, EngineRequest, ExecutionResult
from orchestrator.registry import register_engine
from orchestrator.runtime.client import SkillClient
from orchestrator.runtime.execution import (
    build_action_catalog,
    extract_execution_summary,
    extract_json_object,
    scan_workspace_artifacts,
    summarize_action_results,
)
from orchestrator.runtime.feedback import RunFeedbackReporter
from orchestrator.runtime.prompts import (
    build_action_selection_prompt,
    build_instruction_execution_prompt,
)
from orchestrator.runtime.resolve import ActionResolutionError, ActionResolver
from orchestrator.runtime.run_context import RunContext
from orchestrator.runtime.runners import ActionResult, RunnerExecutionError, RunnerRegistry


UI_CONTRIBUTION = {
    "id": "freestyle",
    "partials": {
        "execute": "modules/orchestrator_freestyle/freestyle-execute.html",
    },
    "scripts": [
        "modules/orchestrator_freestyle/freestyle-execute.js",
    ],
    "modals": [
        "modules/orchestrator_dag/node-log-modal.html",
    ],
}

_DEFAULT_AGENT_TOOLS = ["Bash", "Read", "Write", "Glob", "Grep", "Edit"]
_MAX_ACTION_STEPS = 6


def _action_result_with_artifacts(result: ActionResult, artifacts) -> ActionResult:
    return ActionResult(
        action_id=result.action_id,
        skill_id=result.skill_id,
        runner_name=result.runner_name,
        status=result.status,
        summary=result.summary,
        payload=result.payload,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.return_code,
        artifacts=tuple(artifacts),
        started_at=result.started_at,
        completed_at=result.completed_at,
        latency_ms=result.latency_ms,
        token_usage=dict(result.token_usage),
        metadata=dict(result.metadata),
        error=result.error,
        error_code=result.error_code,
    )


@register_engine("free-style")
class FreestyleEngine:
    """Skills available, but only declared actions may run."""

    ui_contribution = UI_CONTRIBUTION
    meta = EngineMeta(
        label="Free-Style",
        description="Bounded action execution over hydrated skills",
    )

    @classmethod
    def create(
        cls,
        *,
        run_context,
        skill_dir=None,
        log_callback=None,
        allowed_tools=None,
        max_sandbox=None,
        allow_network=None,
        **kw,
    ):
        return cls(
            skill_dir=skill_dir,
            run_context=run_context,
            log_callback=log_callback,
            allowed_tools=allowed_tools,
            max_sandbox=max_sandbox,
            allow_network=allow_network,
        )

    def __init__(
        self,
        skill_dir: Path | str,
        run_context: RunContext,
        log_callback: Optional[Callable[[str, str], None]] = None,
        allowed_tools: Optional[list[str]] = None,
        max_sandbox: str | None = None,
        allow_network: bool | None = None,
    ):
        self.skill_dir = Path(skill_dir)
        self.run_context = run_context
        self.log_callback = log_callback
        self.allowed_tools = list(allowed_tools) if allowed_tools is not None else None
        cfg = get_config()
        self._runtime = cfg.orchestrator_config("free-style").runtime
        self.max_sandbox = max_sandbox or getattr(self._runtime, "max_sandbox", "workspace-write")
        self.allow_network = (
            bool(getattr(self._runtime, "allow_network", False))
            if allow_network is None
            else bool(allow_network)
        )
        self.resolver = ActionResolver(
            max_sandbox=self.max_sandbox,
            allow_network=self.allow_network,
        )
        self.runners = RunnerRegistry()
        self.feedback_reporter = RunFeedbackReporter(
            run_context.run_dir,
            feedback_endpoint=getattr(self._runtime, "feedback_endpoint", ""),
            feedback_auth_token_env=getattr(self._runtime, "feedback_auth_token_env", ""),
            timeout_sec=getattr(self._runtime, "feedback_timeout_sec", 5.0),
            max_retries=getattr(self._runtime, "feedback_max_retries", 0),
        )

    async def run(self, request: EngineRequest) -> ExecutionResult:
        viz = request.visualizer
        if viz:
            auto_node = {
                "id": "FreeStyleExecution",
                "name": "FreeStyleExecution",
                "type": "primary",
                "depends_on": [],
                "purpose": "Execute only declared skill actions",
                "outputs_summary": "Task output",
            }
            await viz.set_nodes([auto_node], [[auto_node["id"]]])
            await viz.update_status("FreeStyleExecution", "running")

        result = await self.execute(
            task=request.task,
            skills=request.skills,
            files=request.files,
            copy_all_skills=request.copy_all_skills,
        )

        if viz:
            status = "completed" if result.status == "completed" else "failed"
            await viz.update_status("FreeStyleExecution", status)

        return result

    async def execute(
        self,
        task: str,
        skills: list[str],
        files: Optional[list[str]] = None,
        copy_all_skills: bool = False,
    ) -> ExecutionResult:
        run_context = self.run_context

        await run_context.async_setup(skills, self.skill_dir, copy_all=copy_all_skills)
        if files:
            await run_context.async_copy_files(files)
        await run_context.async_save_meta(task, "free-style", skills, copy_all=copy_all_skills)

        cwd = str(run_context.exec_dir)
        output_dir = run_context.workspace_dir
        installs = run_context.list_installs()
        action_catalog = build_action_catalog(installs)

        sink_key = f"freestyle-{run_context.run_id}"
        sink_id = add_file_sink(run_context.get_log_path("execution"), filter_key=sink_key)
        execution_logger = _logger.bind(sink_key=sink_key)
        execution_logger.info(f"{'='*60}\nTask: free-style execution\n{'='*60}")
        execution_logger.info(f"Description: {task}")
        execution_logger.info("Mode: free-style")
        execution_logger.info(f"Skills: {', '.join(skills) if skills else '(none)'}")
        execution_logger.info(f"{'-'*60}\nExecution Log\n{'-'*60}")

        def _log_callback(message: str, level: str = "info") -> None:
            execution_logger.log(map_level(level), message)
            if self.log_callback:
                self.log_callback(message, level)

        try:
            if not action_catalog:
                result = ExecutionResult(
                    status="failed",
                    error="No declared actions available for selected skills",
                    metadata={
                        "selected_actions": [],
                        "actions_executed": [],
                        "feedback_status": "not_applicable",
                    },
                )
                await run_context.async_save_result(
                    {
                        "status": result.status,
                        "error": result.error,
                        "mode": "free-style",
                        "selected_skills": skills,
                        "actions_executed": [],
                        "artifacts": [],
                        "metadata": dict(result.metadata),
                    }
                )
                return result

            action_results: list[ActionResult] = []
            selected_actions: list[str] = []
            max_steps = _MAX_ACTION_STEPS
            step = 0

            while step < max_steps:
                decision = await self._select_next_action(
                    task=task,
                    action_catalog=action_catalog,
                    prior_steps=action_results,
                    working_dir=cwd,
                    output_dir=str(output_dir),
                )
                if decision.get("status") == "finish":
                    break

                skill_id = str(decision.get("skill_id") or "").strip()
                action_id = str(decision.get("action_id") or "").strip()
                action_input = decision.get("input") or {}
                if not isinstance(action_input, dict):
                    action_input = {}

                install = run_context.get_install(skill_id)
                if install is None:
                    raise ActionResolutionError(f"Selected skill is not installed: {skill_id!r}")

                resolved = self.resolver.resolve_install(install, action_id=action_id or None)
                action_result = await self._execute_declared_action(
                    task=task,
                    resolved_action=resolved,
                    action_input=action_input,
                    working_dir=cwd,
                    output_dir=output_dir,
                    log_callback=_log_callback,
                )
                selected_actions.append(f"{resolved.skill_id}:{resolved.action_id}")
                action_results.append(action_result)
                self.feedback_reporter.report(
                    self._feedback_from_action("free-style", resolved, action_result)
                )
                step += 1

                if not action_result.is_success:
                    break

                if len(action_catalog) == 1:
                    break
            else:
                action_results.append(
                    ActionResult.failure(
                        action_id="selection",
                        skill_id="runtime",
                        runner_name="freestyle",
                        error=f"Exceeded freestyle step limit ({max_steps})",
                        error_code="step_limit_exceeded",
                    )
                )

            artifacts = scan_workspace_artifacts(run_context.workspace_dir, producer="runtime", role="workspace")
            summary = summarize_action_results([item.to_dict() for item in action_results])
            failed = next((item for item in action_results if not item.is_success), None)
            status = "completed"
            error = None
            if failed is not None:
                status = "partial" if any(item.is_success for item in action_results) else "failed"
                error = failed.error or failed.summary or "Action execution failed"
            feedback_status = (
                self.feedback_reporter.wait_for_pending_sends()
                if selected_actions
                else "not_applicable"
            )

            result = ExecutionResult(
                status=status,
                summary=summary,
                error=error,
                artifacts=[artifact.path for artifact in artifacts],
                metadata={
                    "actions_executed": list(selected_actions),
                    "selected_actions": list(selected_actions),
                    "action_results": [item.to_dict() for item in action_results],
                    "feedback_status": feedback_status,
                    "artifacts": [artifact.to_dict() for artifact in artifacts],
                },
            )

            await run_context.async_save_result(
                {
                    "run_id": run_context.run_id,
                    "status": result.status,
                    "summary": result.summary,
                    "error": result.error,
                    "mode": "free-style",
                    "selected_skills": skills,
                    "actions_executed": list(selected_actions),
                    "artifacts": result.metadata["artifacts"],
                    "metadata": {
                        "selected_actions": list(selected_actions),
                        "feedback_status": result.metadata["feedback_status"],
                    },
                }
            )

            return result
        except (ActionResolutionError, RunnerExecutionError, ValueError) as exc:
            feedback_status = self.feedback_reporter.wait_for_pending_sends()
            await run_context.async_save_result(
                {
                    "run_id": run_context.run_id,
                    "status": "failed",
                    "error": str(exc),
                    "mode": "free-style",
                    "selected_skills": skills,
                    "actions_executed": [],
                    "artifacts": [],
                    "metadata": {
                        "selected_actions": [],
                        "feedback_status": feedback_status,
                    },
                }
            )
            return ExecutionResult(
                status="failed",
                error=str(exc),
                metadata={
                    "selected_actions": [],
                    "actions_executed": [],
                    "feedback_status": feedback_status,
                },
            )
        finally:
            await run_context.async_finalize()
            _logger.remove(sink_id)

    async def _select_next_action(
        self,
        *,
        task: str,
        action_catalog: list[dict],
        prior_steps: list[ActionResult],
        working_dir: str,
        output_dir: str,
    ) -> dict:
        if len(action_catalog) == 1 and not prior_steps:
            item = action_catalog[0]
            return {
                "status": "select",
                "skill_id": item["skill_id"],
                "action_id": item["action_id"],
                "input": {},
                "summary": "Single declared action available",
            }

        prompt = build_action_selection_prompt(
            task=task,
            action_catalog=action_catalog,
            working_dir=working_dir,
            output_dir=output_dir,
            prior_steps=[item.to_dict() for item in prior_steps],
            max_steps=_MAX_ACTION_STEPS,
        )
        async with SkillClient(
            session_id=f"freestyle-select-{self.run_context.run_id}",
            cwd=working_dir,
            log_callback=self.log_callback,
            allowed_tools=self.allowed_tools or _DEFAULT_AGENT_TOOLS,
            disallowed_tools=["Skill"],
            model=self._runtime.model,
        ) as client:
            coro = client.execute(prompt)
            if self._runtime.execution_timeout > 0:
                response = await asyncio.wait_for(coro, timeout=self._runtime.execution_timeout)
            else:
                response = await coro

        payload = extract_json_object(response)
        if not isinstance(payload, dict):
            raise ValueError("Freestyle action selection did not return valid JSON")
        return payload

    async def _execute_declared_action(
        self,
        *,
        task: str,
        resolved_action,
        action_input: dict,
        working_dir: str,
        output_dir: Path,
        log_callback: Callable[[str, str], None],
    ) -> ActionResult:
        if resolved_action.runner_name != "instruction":
            result = await self.runners.run(
                resolved_action,
                action_input,
                workspace_dir=output_dir,
            )
            scanned = scan_workspace_artifacts(output_dir, producer=resolved_action.skill_id, role=resolved_action.action_id)
            if scanned:
                return _action_result_with_artifacts(result, scanned)
            return result

        prepared = await self.runners.run(
            resolved_action,
            action_input,
            workspace_dir=output_dir,
        )
        instruction = ""
        if isinstance(prepared.payload, dict):
            instruction = str(prepared.payload.get("instruction_prompt") or prepared.payload.get("instruction") or "")

        prompt = build_instruction_execution_prompt(
            task=task,
            instruction=instruction,
            output_dir=str(output_dir),
            working_dir=working_dir,
        )
        async with SkillClient(
            session_id=f"freestyle-instruction-{self.run_context.run_id}-{resolved_action.action_id}",
            cwd=working_dir,
            log_callback=log_callback,
            allowed_tools=self.allowed_tools or _DEFAULT_AGENT_TOOLS,
            disallowed_tools=["Skill"],
            model=self._runtime.model,
        ) as client:
            coro = client.execute(prompt)
            if self._runtime.execution_timeout > 0:
                response = await asyncio.wait_for(coro, timeout=self._runtime.execution_timeout)
            else:
                response = await coro
            sdk_metrics = client.last_result_metrics
            metrics_dict = sdk_metrics.to_dict() if sdk_metrics else {}

        summary, is_success = extract_execution_summary(response)
        artifacts = scan_workspace_artifacts(output_dir, producer=resolved_action.skill_id, role=resolved_action.action_id)
        metadata = {
            "instruction_payload": prepared.payload,
            "response": response,
            "sdk_metrics": metrics_dict,
            "token_usage": metrics_dict,
        }
        if is_success:
            return ActionResult.success(
                action_id=resolved_action.action_id,
                skill_id=resolved_action.skill_id,
                runner_name="instruction",
                summary=summary or prepared.summary,
                payload={"response": response, "instruction_payload": prepared.payload},
                artifacts=artifacts,
                latency_ms=prepared.latency_ms,
                token_usage=metrics_dict,
                metadata=metadata,
            )
        return ActionResult.failure(
            action_id=resolved_action.action_id,
            skill_id=resolved_action.skill_id,
            runner_name="instruction",
            error=summary or "Instruction execution failed",
            error_code="instruction_failed",
            latency_ms=prepared.latency_ms,
            metadata=metadata,
        )

    def _feedback_from_action(self, mode: str, resolved_action, action_result: ActionResult):
        from orchestrator.runtime.envelope import RunFeedbackEnvelope

        layer_source = str(resolved_action.metadata.get("layer_source", "active"))
        return RunFeedbackEnvelope.from_action_result(
            run_id=self.run_context.run_id,
            mode=mode,
            layer_source=layer_source,
            resolved_action=resolved_action,
            result=action_result,
        )
