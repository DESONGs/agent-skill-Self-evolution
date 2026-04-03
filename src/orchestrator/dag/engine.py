"""Skill Orchestrator - coordinates multiple skills using ClaudeSDKClient."""

import asyncio
import json
import re
import time
import traceback
from pathlib import Path
from typing import Optional

from config import get_config
from orchestrator.runtime.client import SkillClient
from orchestrator.runtime.models import (
    SDKMetrics,
    SkillMetadata,
    NodeStatus,
    NodeFailureReason,
    NodeExecutionResult,
    ExecutionPhase,
)
from .skill_registry import SkillRegistry
from .graph import DependencyGraph, build_graph_from_nodes
from .prompts import build_planner_prompt
from orchestrator.runtime.feedback import RunFeedbackReporter
from orchestrator.runtime.execution import (
    extract_execution_summary,
    scan_workspace_artifacts,
)
from orchestrator.runtime.prompts import build_direct_executor_prompt, build_instruction_execution_prompt
from orchestrator.runtime.resolve import ActionResolutionError, ActionResolver
from orchestrator.runtime.runners import ActionResult, RunnerExecutionError, RunnerRegistry
from .throttler import ExecutionThrottler
from orchestrator.runtime.run_context import RunContext
from loguru import logger as _logger
from logging_config import add_file_sink, map_level
from orchestrator.base import ExecutionResult, EngineRequest, EngineMeta
from orchestrator.registry import register_engine
from orchestrator.visualizers import VisualizerProtocol, NullVisualizer


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from text response."""
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


UI_CONTRIBUTION = {
    "id": "dag",
    "partials": {
        "execute": "modules/orchestrator_dag/dag-execute.html",
    },
    "scripts": [
        "modules/orchestrator_dag/dag-plan.js",
        "modules/orchestrator_dag/dag-execute.js",
    ],
    "modals": [
        "modules/orchestrator_dag/plan-selection-modal.html",
        "modules/orchestrator_dag/plan-preview-modal.html",
        "modules/orchestrator_dag/node-log-modal.html",
    ],
}

_DEFAULT_AGENT_TOOLS = ["Bash", "Read", "Write", "Glob", "Grep", "Edit"]


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


@register_engine("dag")
class SkillOrchestrator:
    """Orchestrator that uses a single ClaudeSDKClient to maintain context.

    Workflow:
    1. Load skills
    2. Generate execution plan
    3. Execute nodes (all in same session, context preserved)
    """

    ui_contribution = UI_CONTRIBUTION
    meta = EngineMeta(
        label="DAG",
        description="Pre-plan execution with DAG visualization",
        execution_visual="graph",
        initial_phase="planning",
    )

    @classmethod
    def create(
        cls,
        *,
        run_context,
        skill_dir=None,
        log_callback=None,
        max_concurrent=3,
        max_sandbox=None,
        allow_network=None,
        **kw,
    ):
        return cls(
            skill_dir=str(skill_dir) if skill_dir else None,
            run_context=run_context,
            logs_dir=run_context.logs_dir,
            max_sandbox=max_sandbox,
            allow_network=allow_network,
        )

    def __init__(
        self,
        skill_dir: str = ".claude/skills",
        workspace_dir: str = "workspace",
        max_concurrent: Optional[int] = None,
        node_timeout: Optional[float] = None,
        run_context: Optional[RunContext] = None,
        logs_dir: Optional[Path] = None,
        max_sandbox: str | None = None,
        allow_network: bool | None = None,
    ):
        cfg = get_config()
        ocfg = cfg.orchestrator_config()
        self.skill_dir = Path(skill_dir)
        self.run_context = run_context
        self.logs_dir = logs_dir
        self._runtime = ocfg.runtime
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
            run_context.run_dir if run_context else Path("runs"),
            feedback_endpoint=getattr(self._runtime, "feedback_endpoint", ""),
            feedback_auth_token_env=getattr(self._runtime, "feedback_auth_token_env", ""),
            timeout_sec=getattr(self._runtime, "feedback_timeout_sec", 5.0),
            max_retries=getattr(self._runtime, "feedback_max_retries", 0),
        )
        self._executed_actions: list[str] = []
        self._action_results: list[dict] = []
        # If run_context exists, use its workspace_dir and logs_dir
        if run_context:
            self.workspace_dir = run_context.workspace_dir
            if not self.logs_dir:
                self.logs_dir = run_context.logs_dir
        else:
            self.workspace_dir = Path(workspace_dir)
        self.registry = SkillRegistry(str(skill_dir))
        self.client: Optional[SkillClient] = None
        self.graph: Optional[DependencyGraph] = None
        self.visualizer: Optional[VisualizerProtocol] = None
        self.current_task: str = ""  # Store task for node execution context
        _max_concurrent = max_concurrent if max_concurrent is not None else ocfg.max_concurrent
        self.throttler = ExecutionThrottler(max_concurrent=_max_concurrent)
        self.node_timeout = node_timeout if node_timeout is not None else ocfg.node_timeout
        # Background task registry to prevent fire-and-forget garbage collection
        self._background_tasks: set[asyncio.Task] = set()
        # Log queue for async log handling (bounded to prevent memory exhaustion)
        self._log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._log_worker_task: Optional[asyncio.Task] = None
        self._dropped_logs: int = 0  # Track dropped logs for monitoring
        # SDK metrics collection
        self._planning_metrics: Optional[SDKMetrics] = None
        self._phase_node_metrics: list[list[tuple[str, SDKMetrics]]] = []
        # File logger for orchestrator (when logs_dir is set)
        self._orchestrator_sink_id: Optional[int] = None
        self._orchestrator_logger = None
        if self.logs_dir:
            sink_key = f"orch-{id(self)}"
            self._orchestrator_sink_id = add_file_sink(
                self.logs_dir / "orchestrator.log", filter_key=sink_key
            )
            self._orchestrator_logger = _logger.bind(sink_key=sink_key)


    def _start_log_worker(self) -> None:
        """Start the log worker coroutine."""
        if self._log_worker_task is None:
            self._log_worker_task = asyncio.create_task(self._log_worker())

    async def _stop_log_worker(self) -> None:
        """Stop the log worker and flush remaining logs."""
        if self._log_worker_task:
            # Signal worker to stop
            await self._log_queue.put(None)
            await self._log_worker_task
            self._log_worker_task = None

    async def _log_worker(self) -> None:
        """Process logs from queue sequentially."""
        while True:
            item = await self._log_queue.get()
            if item is None:
                # Drain remaining logs
                while not self._log_queue.empty():
                    remaining = self._log_queue.get_nowait()
                    if remaining is not None:
                        await self._process_log(remaining)
                break
            await self._process_log(item)

    async def _process_log(self, item: tuple) -> None:
        """Process a single log item."""
        message, level, node_id = item
        if self.visualizer:
            await self.visualizer.add_log(message, level, node_id=node_id)

    def _enqueue_log(self, message: str, level: str = "info", node_id: Optional[str] = None) -> None:
        """Enqueue a log message for async processing.

        Also writes to file logger if configured.
        Uses bounded queue - logs are dropped if queue is full to prevent memory exhaustion.
        """
        # Write to orchestrator file log (always, for batch mode)
        if self._orchestrator_logger:
            prefix = f"[{node_id}] " if node_id else ""
            self._orchestrator_logger.log(map_level(level), f"{prefix}{message}")

        try:
            self._log_queue.put_nowait((message, level, node_id))
        except asyncio.QueueFull:
            # Queue is full - drop the log and track it
            self._dropped_logs += 1
            # Log to file that we're dropping logs (every 100 drops)
            if self._dropped_logs % 100 == 1 and self._orchestrator_logger:
                self._orchestrator_logger.warning(
                    f"Log queue full, {self._dropped_logs} logs dropped so far"
                )

    async def run(self, request: EngineRequest) -> ExecutionResult:
        """Unified engine interface. Delegates to run_with_visualizer."""
        visualizer = request.visualizer or NullVisualizer()
        return await self.run_with_visualizer(
            task=request.task,
            skill_names=request.skills,
            visualizer=visualizer,
            files=request.files,
        )

    async def run_with_visualizer(
        self,
        task: str,
        skill_names: list[str],
        visualizer: VisualizerProtocol,
        context: Optional[dict] = None,
        plan_only: bool = False,
        files: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """Run orchestration with an external visualizer.

        Args:
            task: Task description
            skill_names: List of skill names to use
            visualizer: Visualizer instance (Rich or Textual)
            context: Optional context dict
            plan_only: If True, stop after generating plan
            files: Optional list of files to copy into run context
        """
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        result = {"status": "unknown"}

        self.visualizer = visualizer
        self.current_task = task  # Store for node execution context
        self._executed_actions = []
        self._action_results = []
        self._planning_metrics = None
        self._phase_node_metrics = []
        viz = visualizer
        # Start log worker for async log processing
        self._start_log_worker()
        await viz.set_task(task)
        await viz.add_log(f"Starting orchestration with skills: {', '.join(skill_names)}", "info")

        # Setup run_context isolated environment
        if self.run_context:
            await viz.add_log(f"Setting up isolated run: {self.run_context.run_id}", "info")
            await self.run_context.async_setup(skill_names, self.skill_dir)
            if files:
                copied = await self.run_context.async_copy_files(files)
                await viz.add_log(f"Files copied to workspace: {copied}", "info")
            await self.run_context.async_save_meta(task, "dag", skill_names)
            if files:
                self.run_context.update_meta(files=files)
            await viz.add_log(f"Skills copied to: {self.run_context.skills_dir}", "info")

        try:
            try:
                # Step 1: Load skills
                await viz.add_log("Loading skills...", "info")
                skills = self.registry.find_by_names(skill_names)
                missing = self.registry.get_missing(skill_names)
                if missing:
                    await viz.add_log(f"Skills not found: {missing}", "error")
                    return ExecutionResult(status="failed", error=f"Skills not found: {missing}")
                await viz.add_log(f"Loaded {len(skills)} skills", "ok")

                # Step 2: Generate plans
                # Single skill optimization: skip planning API call
                if len(skills) == 0:
                    await viz.add_log("No skills selected, Claude will handle directly", "info")
                    direct_node = {
                        "id": "ClaudeDirect",
                        "name": "ClaudeDirect",
                        "type": "primary",
                        "depends_on": [],
                        "purpose": "Directly complete the task using available tools",
                        "outputs_summary": "Task output",
                        "downstream_hint": "",
                        "usage_hints": {}
                    }
                    plans_result = {"plans": [{"name": "Direct Execution", "nodes": [direct_node]}]}
                elif len(skills) == 1:
                    await viz.add_log("Single skill detected, skipping orchestration", "info")
                    skill = skills[0]
                    single_node = {
                        "id": skill.name,
                        "name": skill.name,
                        "action_id": skill.resolved_default_action_id(),
                        "input": {},
                        "type": "primary",
                        "depends_on": [],
                        "purpose": f"Execute {skill.name}",
                        "outputs_summary": "Task output",
                        "downstream_hint": "",
                        "usage_hints": {}
                    }
                    plans_result = {"plans": [{"name": "Direct Execution", "nodes": [single_node]}]}
                else:
                    await viz.add_log("Generating execution plans...", "info")
                    # Use log queue for synchronous callback from SkillClient
                    def main_log_callback(message: str, level: str = "info") -> None:
                        self._enqueue_log(message, level)
                    async with SkillClient(
                        session_id=f"orch-{task[:20]}",
                        cwd=str(self.run_context.exec_dir),
                        log_callback=main_log_callback,
                        model=self._runtime.model,
                    ) as client:
                        self.client = client
                        plans_result = await self._generate_plans(task, skills, context)
                        self._planning_metrics = client.last_result_metrics

                if "error" in plans_result:
                    await viz.add_log(f"Planning failed: {plans_result['error']}", "error")
                    return ExecutionResult(status="failed", error=plans_result["error"])

                plans = plans_result.get("plans", [])
                await viz.add_log(f"Generated {len(plans)} plans", "ok")

                if plan_only:
                    await viz.add_log("Stopped after planning (plan_only mode)", "info")
                    return ExecutionResult(
                        status="plan_only",
                        metadata={"plans": plans},
                    )

                # Let user select a plan (or auto-select if only one)
                if len(plans) > 1:
                    await viz.add_log(f"Waiting for user to select from {len(plans)} plans...", "info")
                    selected_index = await viz.select_plan(plans)
                else:
                    selected_index = 0

                selected_plan = plans[selected_index] if plans else {"nodes": []}

                # Notify frontend: planning is done, transitioning to executing
                await viz.set_workflow_phase("executing")

                self.graph = build_graph_from_nodes(selected_plan["nodes"])
                phases = self.graph.get_execution_phases()

                # Save selected execution plan
                if self.run_context:
                    self.run_context.save_plan(selected_plan)

                # Initialize visualizer with nodes
                await viz.set_nodes(selected_plan["nodes"], phases)
                await viz.add_log(f"Selected plan: {selected_plan.get('name', 'Default')}", "info")

                # Step 3: Execute nodes in parallel phases
                for phase_idx, phase in enumerate(phases, 1):
                    await viz.set_phase(phase_idx)
                    await viz.add_log(
                        f"Starting phase {phase_idx}/{len(phases)} "
                        f"({len(phase.nodes)} nodes, mode: {phase.mode})",
                        "info"
                    )

                    # Mark all nodes in phase as running
                    for node_id in phase.nodes:
                        await viz.update_status(node_id, "running")

                    # Execute phase (parallel or sequential based on mode)
                    phase_results = await self._execute_phase_parallel(phase)

                    # Update visualizer with results
                    phase_metrics_list: list[tuple[str, SDKMetrics]] = []
                    for node_result in phase_results:
                        status = "completed" if node_result.status == NodeStatus.COMPLETED else "failed"
                        await viz.update_status(node_result.node_id, status)

                        # Collect SDK metrics from this node
                        if node_result.sdk_metrics:
                            fields = SDKMetrics.__dataclass_fields__
                            m = SDKMetrics(**{k: v for k, v in node_result.sdk_metrics.items()
                                            if k in fields})
                            phase_metrics_list.append((node_result.node_id, m))

                        if node_result.status == NodeStatus.COMPLETED:
                            await viz.add_log(
                                f"Node {node_result.node_id} completed "
                                f"({node_result.execution_time_seconds:.1f}s)",
                                "ok"
                            )
                            if node_result.summary:
                                await viz.add_log(f"  Summary: {node_result.summary}", "info")
                        else:
                            await viz.add_log(
                                f"Node {node_result.node_id} failed: {node_result.error or 'unknown'}",
                                "error"
                            )
                    self._phase_node_metrics.append(phase_metrics_list)

                # Finalize
                stats = self.graph.get_stats()
                result["status"] = "completed" if stats["failed"] == 0 else "partial"
                result["stats"] = stats
                result["mode"] = "dag"
                result["selected_skills"] = list(skill_names)
                result["actions_executed"] = list(self._executed_actions)
                result["selected_actions"] = list(self._executed_actions)
                result["action_results"] = list(self._action_results)
                result["feedback_status"] = (
                    self.feedback_reporter.wait_for_pending_sends()
                    if self._executed_actions
                    else "not_applicable"
                )
                result["artifacts"] = [
                    artifact.to_dict()
                    for artifact in scan_workspace_artifacts(
                        self.workspace_dir,
                        producer="runtime",
                        role="workspace",
                    )
                ]
                await viz.add_log(f"Completed: {stats['completed']}/{stats['total']} nodes", "ok")

            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)
                await viz.add_log(f"Error: {e}", "error")
                await viz.add_log(traceback.format_exc(), "error")

            # Aggregate SDK metrics (even on partial failure, preserves completed nodes)
            extra = {}
            if self._planning_metrics:
                extra["planning"] = self._planning_metrics
            if self._phase_node_metrics or extra:
                result["sdk_metrics"] = SDKMetrics.aggregate(
                    self._phase_node_metrics, extra_metrics=extra
                )

            # Save execution result
            result.setdefault(
                "feedback_status",
                self.feedback_reporter.wait_for_pending_sends()
                if self._executed_actions
                else "not_applicable",
            )
            if self.run_context:
                await self.run_context.async_save_result(result)
                await viz.add_log(f"Results saved to: {self.run_context.run_dir}", "info")
        finally:
            # Always finalize (copy workspace back, clean up temp) even on error
            if self.run_context:
                await self.run_context.async_finalize()

        # Stop log worker and flush remaining logs
        await self._stop_log_worker()
        # Clean up file sink
        if self._orchestrator_sink_id is not None:
            _logger.remove(self._orchestrator_sink_id)
            self._orchestrator_sink_id = None
        self.visualizer = None
        return ExecutionResult(
            status=result.get("status", "unknown"),
            error=result.get("error"),
            artifacts=[artifact.get("path", "") for artifact in result.get("artifacts", []) if artifact.get("path")],
            metadata={k: v for k, v in result.items() if k not in ("status", "error", "artifacts")},
        )

    async def _generate_plans(self, task: str, skills: list[SkillMetadata], context: Optional[dict]) -> dict:
        """Generate multiple execution plans using the client."""
        # Include skill names, descriptions, and content for planning
        skill_info_parts = []
        for s in skills:
            action_ids = ", ".join(s.declared_action_ids()) or "(default only)"
            default_action = s.resolved_default_action_id() or ""
            skill_info_parts.append(
                f"### Skill: {s.name}\n"
                f"{s.description}\n"
                f"\nDeclared actions: {action_ids}\n"
                f"Default action: {default_action}\n"
                f"\n#### Content:\n{s.content}"
            )
        skill_info = "\n\n".join(skill_info_parts)

        context_str = f"\nContext: {json.dumps(context)}" if context else ""

        prompt = build_planner_prompt(task, skill_info, context_str)
        response = await self.client.execute(prompt)
        result = extract_json(response)

        if not result:
            return {"error": "Failed to parse response"}

        # Handle both old format {"nodes": [...]} and new format {"plans": [...]}
        if "plans" in result:
            return result
        elif "nodes" in result:
            return {"plans": [{"name": "Default Plan", "description": "Single execution plan", "nodes": result["nodes"]}]}

        return {"error": "Invalid plan format"}

    async def _execute_node(self, node_id: str) -> dict:
        """Backward-compatible wrapper around isolated action execution."""
        node_result = await self._execute_node_isolated(node_id)
        payload = {
            "status": "completed" if node_result.status == NodeStatus.COMPLETED else "failed",
            "output_path": node_result.output_path,
            "summary": node_result.summary,
        }
        if node_result.error:
            payload["error"] = node_result.error
        return payload

    async def _execute_phase_parallel(
        self, phase: ExecutionPhase
    ) -> list[NodeExecutionResult]:
        """Execute all nodes in a phase concurrently using isolated sessions.

        Args:
            phase: The execution phase containing nodes to execute

        Returns:
            List of NodeExecutionResult for each node
        """
        # Build tasks for throttler
        tasks = [
            (lambda nid=node_id: self._execute_node_isolated(nid), node_id)
            for node_id in phase.nodes
        ]

        # Execute with throttling
        results = await self.throttler.execute_batch(tasks)

        # Update graph state and cascade failures
        for result in results:
            if result.status == NodeStatus.COMPLETED:
                self.graph.update_status(
                    result.node_id, "completed", result.output_path
                )
            else:
                self.graph.fail_node(result.node_id)

        return results

    async def _execute_node_isolated(self, node_id: str) -> NodeExecutionResult:
        """Execute a single node in a completely isolated session.

        This creates an independent session for the node, preventing context
        pollution between nodes and enabling true parallel execution.

        Args:
            node_id: The ID of the node to execute

        Returns:
            NodeExecutionResult with execution details
        """
        node = self.graph.get_node(node_id)

        # Special handling: Claude Direct node (no skill)
        if node.name == "ClaudeDirect":
            return await self._execute_claude_direct(node_id, node)

        skill = self.registry.get(node.name)
        start_time = time.time()

        if not skill:
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=f"Skill {node.name} not found",
                failure_reason=NodeFailureReason.SKILL_ERROR,
                execution_time_seconds=time.time() - start_time,
            )

        output_dir = self.workspace_dir
        cwd = str(self.run_context.exec_dir) if self.run_context else str(self.workspace_dir)
        artifacts_context = self._build_artifacts_context(node_id)

        # Create log callback that includes node_id
        # Use log queue for synchronous callback from SkillClient
        # Also create node-specific file logger if logs_dir is set
        node_sink_id: Optional[int] = None
        node_logger = None
        if self.logs_dir:
            sink_key = f"node-{node_id}-{id(self)}"
            node_sink_id = add_file_sink(
                self.logs_dir / f"node_{node_id}.log", filter_key=sink_key
            )
            node_logger = _logger.bind(sink_key=sink_key)
            node_logger.info(f"{'='*60}\nNode: {node_id} ({node.name})\n{'='*60}")
            node_logger.info(f"Purpose: {node.purpose}")
            node_logger.info(f"Output dir: {output_dir}")
            node_logger.info(f"{'-'*60}\nExecution Log\n{'-'*60}")

        def node_log_callback(message: str, level: str = "info") -> None:
            # Write to node-specific log file
            if node_logger:
                node_logger.log(map_level(level), message)
            self._enqueue_log(message, level, node_id=node_id)

        try:
            install = self.run_context.get_install(node.name) if self.run_context else None
            resolved = (
                self.resolver.resolve_install(
                    install,
                    action_id=node.action_id or skill.resolved_default_action_id(),
                )
                if install is not None
                else self.resolver.resolve(
                    Path(skill.path),
                    action_id=node.action_id or skill.resolved_default_action_id(),
                    install_root=self.workspace_dir / ".runtime-installs",
                )
            )

            action_result = await self._execute_resolved_action(
                node_id=node_id,
                resolved_action=resolved,
                action_input=node.action_input,
                output_dir=output_dir,
                working_dir=cwd,
                artifacts_context=artifacts_context,
                log_callback=node_log_callback,
            )
            self._executed_actions.append(f"{resolved.skill_id}:{resolved.action_id}")
            self._action_results.append(action_result.to_dict())
            self.feedback_reporter.report(
                self._feedback_from_action("dag", resolved, action_result)
            )

            node_metrics = action_result.metadata.get("sdk_metrics")
            if action_result.is_success:
                return NodeExecutionResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED,
                    output_path=str(output_dir),
                    summary=action_result.summary,
                    failure_reason=NodeFailureReason.SUCCESS,
                    execution_time_seconds=time.time() - start_time,
                    sdk_metrics=node_metrics if isinstance(node_metrics, dict) else None,
                )
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                output_path=str(output_dir),
                summary=action_result.summary,
                error=action_result.error or "Action execution failed",
                failure_reason=NodeFailureReason.EXECUTION_ERROR,
                execution_time_seconds=time.time() - start_time,
                sdk_metrics=node_metrics if isinstance(node_metrics, dict) else None,
            )

        except asyncio.TimeoutError:
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=f"Execution timed out after {self.node_timeout}s",
                failure_reason=NodeFailureReason.TIMEOUT,
                execution_time_seconds=self.node_timeout,
            )
        except (ActionResolutionError, RunnerExecutionError, ValueError) as e:
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                failure_reason=NodeFailureReason.UNKNOWN,
                execution_time_seconds=time.time() - start_time,
            )
        finally:
            if node_sink_id is not None:
                _logger.remove(node_sink_id)

    async def _execute_resolved_action(
        self,
        *,
        node_id: str,
        resolved_action,
        action_input: dict,
        output_dir: Path,
        working_dir: str,
        artifacts_context: str,
        log_callback,
    ) -> ActionResult:
        if resolved_action.runner_name != "instruction":
            result = await self.runners.run(
                resolved_action,
                action_input,
                workspace_dir=output_dir,
            )
            scanned = scan_workspace_artifacts(
                output_dir,
                producer=resolved_action.skill_id,
                role=resolved_action.action_id,
            )
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
            instruction = str(
                prepared.payload.get("instruction_prompt")
                or prepared.payload.get("instruction")
                or ""
            )

        prompt = build_instruction_execution_prompt(
            task=self.current_task,
            instruction=instruction,
            output_dir=str(output_dir),
            working_dir=working_dir,
            artifacts_context=artifacts_context,
        )
        async with SkillClient(
            session_id=f"node-{node_id}-instruction",
            cwd=working_dir,
            log_callback=log_callback,
            allowed_tools=_DEFAULT_AGENT_TOOLS,
            disallowed_tools=["Skill"],
            model=self._runtime.model,
        ) as client:
            response = await asyncio.wait_for(
                client.execute(prompt),
                timeout=self.node_timeout,
            )
            node_metrics = client.last_result_metrics
            metrics_dict = node_metrics.to_dict() if node_metrics else {}

        summary, is_success = extract_execution_summary(response)
        artifacts = scan_workspace_artifacts(
            output_dir,
            producer=resolved_action.skill_id,
            role=resolved_action.action_id,
        )
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
            run_id=self.run_context.run_id if self.run_context else "",
            mode=mode,
            layer_source=layer_source,
            resolved_action=resolved_action,
            result=action_result,
        )

    def _build_artifacts_context(self, node_id: str) -> str:
        """Build artifacts context string for a node.

        Collects output paths and usage hints from all completed upstream nodes.

        Args:
            node_id: The target node ID

        Returns:
            Formatted string describing available artifacts
        """
        artifact_lines = []

        for nid, n in self.graph.nodes.items():
            if n.status == NodeStatus.COMPLETED and n.output_path:
                usage_hint = n.usage_hints.get(node_id, "")
                if usage_hint:
                    artifact_lines.append(
                        f"### {nid} ({n.name})\n"
                        f"- Path: {n.output_path}\n"
                        f"- How to use: {usage_hint}"
                    )
                else:
                    artifact_lines.append(
                        f"### {nid} ({n.name})\n"
                        f"- Path: {n.output_path}"
                    )

        if artifact_lines:
            return "\n\n".join(artifact_lines)
        return "None (this is the first node)"

    def _extract_execution_summary(self, response: str) -> tuple[str, bool]:
        """Extract execution summary and status from a standard response."""
        return extract_execution_summary(response)

    async def _execute_claude_direct(self, node_id: str, node) -> NodeExecutionResult:
        """Execute task directly with Claude without any skill."""
        start_time = time.time()

        output_dir = self.workspace_dir

        # Determine cwd
        cwd = str(self.run_context.exec_dir) if self.run_context else str(self.workspace_dir)

        # Build direct execution prompt with working directory constraint
        prompt = build_direct_executor_prompt(
            task=self.current_task,
            output_dir=str(output_dir),
            working_dir=cwd,
        )

        # Create node-specific file logger if logs_dir is set
        node_sink_id: Optional[int] = None
        node_logger = None
        if self.logs_dir:
            sink_key = f"node-{node_id}-{id(self)}"
            node_sink_id = add_file_sink(
                self.logs_dir / f"node_{node_id}.log", filter_key=sink_key
            )
            node_logger = _logger.bind(sink_key=sink_key)
            node_logger.info(f"{'='*60}\nNode: {node_id} (ClaudeDirect)\n{'='*60}")
            node_logger.info(f"Task: {self.current_task}")
            node_logger.info(f"Output dir: {output_dir}")
            node_logger.info(f"{'-'*60}\nExecution Log\n{'-'*60}")

        def node_log_callback(message: str, level: str = "info") -> None:
            # Write to node-specific log file
            if node_logger:
                node_logger.log(map_level(level), message)
            self._enqueue_log(message, level, node_id=node_id)

        try:

            # Disable Skill tool since no skills are available
            async with SkillClient(
                session_id=f"node-{node_id}",
                cwd=cwd,
                log_callback=node_log_callback,
                disallowed_tools=["Skill"],
                model=self._runtime.model,
            ) as client:
                response = await asyncio.wait_for(
                    client.execute(prompt),
                    timeout=self.node_timeout,
                )
                node_metrics = client.last_result_metrics
                metrics_dict = node_metrics.to_dict() if node_metrics else None

                summary, is_success = self._extract_execution_summary(response)

                return NodeExecutionResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED if is_success else NodeStatus.FAILED,
                    output_path=str(output_dir),
                    summary=summary or "Claude direct execution completed",
                    failure_reason=NodeFailureReason.SUCCESS if is_success else NodeFailureReason.EXECUTION_ERROR,
                    execution_time_seconds=time.time() - start_time,
                    sdk_metrics=metrics_dict,
                )
        except asyncio.TimeoutError:
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=f"Execution timed out after {self.node_timeout}s",
                failure_reason=NodeFailureReason.TIMEOUT,
                execution_time_seconds=self.node_timeout,
            )
        except Exception as e:
            return NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                failure_reason=NodeFailureReason.EXECUTION_ERROR,
                execution_time_seconds=time.time() - start_time,
            )
        finally:
            if node_sink_id is not None:
                _logger.remove(node_sink_id)
