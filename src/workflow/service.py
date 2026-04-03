"""Core workflow: search skills → create run context → run engine.

No UI dependencies — usable from both Web and CLI adapters.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Callable

from loguru import logger

from constants import DEFAULT_BASELINE_TOOLS, resolve_skill_group
from environment import (
    EnvironmentKernel,
    EnvironmentRuntimeDefaults,
    RetrievalSnapshot,
    SkillCandidate,
    normalize_mode_name,
)
from manager import create_manager
from manager.base import RetrievalResult
from orchestrator.base import EngineRequest, ExecutionResult
from orchestrator.registry import create_engine
from orchestrator.runtime.envelope import ArtifactRecord, ResultEnvelope, RunEnvelope
from orchestrator.runtime.run_context import RunContext
from orchestrator.visualizers import NullVisualizer

from .models import TaskRequest, EventCallback


def _manager_layering_mode(cfg) -> str:
    try:
        layering_cfg = cfg.layering_config()
    except Exception:
        return "disabled"
    return getattr(layering_cfg, "mode", "disabled")


def _runtime_execution_timeout(cfg, orchestrator_name: str) -> float | None:
    orch_cfg = cfg.orchestrator_config(orchestrator_name)
    runtime_cfg = getattr(orch_cfg, "runtime", None) if orch_cfg else None
    return getattr(runtime_cfg, "execution_timeout", None)


def _runtime_config(cfg, orchestrator_name: str):
    orch_cfg = cfg.orchestrator_config(orchestrator_name)
    return getattr(orch_cfg, "runtime", None) if orch_cfg else None


def _build_runtime_defaults(cfg, request: TaskRequest) -> EnvironmentRuntimeDefaults:
    configured_orchestrator = str(cfg._get("orchestrator"))
    runtime_cfg = _runtime_config(cfg, configured_orchestrator)
    normalized_mode = normalize_mode_name(request.mode)
    default_tools: tuple[str, ...] = ()
    if request.allowed_tools:
        default_tools = tuple(request.allowed_tools)
    elif normalized_mode == "no-skill":
        default_tools = tuple(DEFAULT_BASELINE_TOOLS)

    return EnvironmentRuntimeDefaults(
        manager_name=cfg.manager,
        orchestrator_name=configured_orchestrator,
        skill_group=request.skill_group or cfg.skill_group,
        max_skills=cfg.max_skills,
        layering_mode=_manager_layering_mode(cfg),
        execution_timeout=getattr(runtime_cfg, "execution_timeout", None),
        default_allowed_tools=default_tools,
        max_sandbox=str(getattr(runtime_cfg, "max_sandbox", "workspace-write")),
        allow_network=bool(getattr(runtime_cfg, "allow_network", False)),
    )


def _build_skill_candidate(skill: dict, *, source_layer: str | None = None) -> SkillCandidate | None:
    skill_id = str(skill.get("id") or skill.get("skill_id") or skill.get("name") or "").strip()
    if not skill_id:
        return None

    raw_actions = skill.get("actions")
    action_count = skill.get("action_count")
    if action_count is None and isinstance(raw_actions, list):
        action_count = len(raw_actions)

    try:
        score = float(skill.get("score") or skill.get("similarity") or skill.get("final_score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0

    try:
        action_count_value = int(action_count or 0)
    except (TypeError, ValueError):
        action_count_value = 0

    requires_dag = bool(
        skill.get("requires_dag")
        or skill.get("mode_hint") == "dag"
        or skill.get("action_graph")
        or skill.get("workflow")
    )

    return SkillCandidate(
        skill_id=skill_id,
        score=score,
        source_layer=str(skill.get("source_layer") or skill.get("layer") or source_layer or "active"),
        requires_dag=requires_dag,
        action_count=action_count_value,
        metadata=dict(skill),
    )


def _normalize_retrieval_result(
    result: RetrievalResult,
    *,
    max_skills: int,
) -> RetrievalSnapshot:
    candidates: list[SkillCandidate] = []
    for skill in result.selected_skills[:max_skills]:
        if not isinstance(skill, dict):
            continue
        candidate = _build_skill_candidate(skill)
        if candidate is not None:
            candidates.append(candidate)

    dormant_raw = result.metadata.get("dormant_suggestions") or []
    dormant_suggestions: list[SkillCandidate] = []
    for skill in dormant_raw:
        if not isinstance(skill, dict):
            continue
        candidate = _build_skill_candidate(skill, source_layer="dormant")
        if candidate is not None:
            dormant_suggestions.append(candidate)

    metadata = dict(result.metadata)
    metadata["selected_skills"] = [candidate.skill_id for candidate in candidates]
    metadata["selected_skill_count"] = len(candidates)

    return RetrievalSnapshot(
        query=result.query,
        candidates=tuple(candidates),
        dormant_suggestions=tuple(dormant_suggestions),
        metadata=metadata,
    )


def _discover_retrieval(
    task_description: str,
    *,
    skill_group: str,
    event_callback: Optional[EventCallback],
    max_skills: int,
) -> RetrievalSnapshot:
    group = resolve_skill_group(skill_group)
    tree_path = group.get("tree_path")
    vector_db_path = group.get("vector_db_path")

    manager = create_manager(
        tree_path=tree_path,
        vector_db_path=vector_db_path,
        event_callback=event_callback,
    )
    result = manager.search(task_description, verbose=False)
    return _normalize_retrieval_result(result, max_skills=max_skills)


def _registry_metadata_from_retrieval(
    cfg,
    retrieval: RetrievalSnapshot | None,
    *,
    request: TaskRequest,
) -> dict:
    normalized_request_mode = normalize_mode_name(request.mode)
    metadata = {
        "manager_name": cfg.manager,
        "orchestrator_name": str(cfg._get("orchestrator")),
        "layering_mode": _manager_layering_mode(cfg),
    }
    if retrieval is not None:
        if "max_sandbox" in retrieval.metadata:
            metadata["max_sandbox"] = retrieval.metadata["max_sandbox"]
        if "allow_network" in retrieval.metadata:
            metadata["allow_network"] = retrieval.metadata["allow_network"]
        metadata["candidates"] = [
            {
                "skill_id": candidate.skill_id,
                "score": candidate.score,
                "source_layer": candidate.source_layer,
                "requires_dag": candidate.requires_dag,
                "action_count": candidate.action_count,
                **candidate.metadata,
            }
            for candidate in retrieval.candidates
        ]
        metadata["dormant_suggestions"] = [
            {
                "skill_id": candidate.skill_id,
                "score": candidate.score,
                "source_layer": candidate.source_layer,
                **candidate.metadata,
            }
            for candidate in retrieval.dormant_suggestions
        ]
    if cfg.manager == "direct" and normalized_request_mode not in {"dag", "free-style", "no-skill"}:
        metadata["mode"] = "free-style"
    return metadata


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _persist_runtime_snapshots(
    *,
    run_context: RunContext,
    request: TaskRequest,
    mode: str,
    skills: list[str],
    retrieval: RetrievalSnapshot | None,
    profile_payload: dict,
    mode_decision_payload: dict,
    allowed_tools: list[str] | None,
    copy_all_skills: bool,
) -> None:
    run_context.run_dir.mkdir(parents=True, exist_ok=True)

    run_envelope = RunEnvelope(
        run_id=run_context.run_id,
        task=request.task,
        mode=mode,
        skill_group=request.skill_group,
        selected_skills=list(skills),
        files=list(request.files or []),
        allowed_tools=list(allowed_tools) if allowed_tools is not None else None,
        copy_all_skills=copy_all_skills,
        run_dir=run_context.run_dir,
        exec_dir=run_context.exec_dir,
        workspace_dir=run_context.workspace_dir,
        logs_dir=run_context.logs_dir,
        skills_dir=run_context.skills_dir,
        environment=profile_payload,
        retrieval=retrieval.metadata if retrieval else {},
        metadata={
            "mode_decision": mode_decision_payload,
            "runtime_policy": {
                "max_sandbox": profile_payload.get("max_sandbox"),
                "allow_network": profile_payload.get("allow_network"),
            },
        },
    )
    _write_json(run_context.run_dir / "environment.json", profile_payload)
    _write_json(run_context.run_dir / "retrieval.json", retrieval.to_dict() if retrieval else {})
    _write_json(run_context.run_dir / "run_envelope.json", run_envelope.to_dict())


def _persist_result_envelope(
    *,
    run_context: RunContext,
    result: ExecutionResult,
    mode: str,
    skills: list[str],
) -> None:
    actions_executed = list(
        result.metadata.get("actions_executed")
        or result.metadata.get("selected_actions")
        or []
    )
    result_envelope = ResultEnvelope(
        run_id=run_context.run_id,
        status=result.status,
        summary=result.summary,
        error=result.error,
        mode=mode,
        completed_at=result.metadata.get("completed_at"),
        selected_skills=list(skills),
        actions_executed=actions_executed,
        artifacts=[ArtifactRecord(artifact_id=artifact, path=artifact) for artifact in result.artifacts],
        metrics=dict(result.metadata.get("sdk_metrics") or {}),
        metadata={
            key: value
            for key, value in result.metadata.items()
            if key not in {"sdk_metrics", "response", "environment_profile", "mode_decision", "retrieval"}
        },
    )
    _write_json(run_context.run_dir / "result_envelope.json", result_envelope.to_dict())


def discover_skills(
    task_description: str,
    skill_group: str = "skill_seeds",
    event_callback: Optional[EventCallback] = None,
) -> list[str]:
    """Search for relevant skills using the manager.

    Args:
        task_description: The task to search skills for.
        skill_group: Skill group ID.
        event_callback: Optional callback for search progress events.

    Returns:
        List of skill IDs.
    """
    from config import get_config

    cfg = get_config()
    retrieval = _discover_retrieval(
        task_description,
        skill_group=skill_group,
        event_callback=event_callback,
        max_skills=cfg.max_skills,
    )
    return retrieval.selected_skill_ids


async def run_task(
    request: TaskRequest,
    on_event: Optional[EventCallback] = None,
) -> ExecutionResult:
    """Execute a single task through the full workflow.

    Steps:
        1. Resolve skill group
        2. Discover skills (if not pre-specified)
        3. Create RunContext
        4. Instantiate engine via registry
        5. Run engine

    Args:
        request: Task request parameters.
        on_event: Optional progress callback.

    Returns:
        ExecutionResult from the engine.
    """
    # 1. Resolve skill group → get skill_dir
    group = resolve_skill_group(request.skill_group)
    skill_dir = Path(group["skills_dir"])

    # 2. Discover skills (if needed)
    from config import get_config

    cfg = get_config()
    kernel = EnvironmentKernel(_build_runtime_defaults(cfg, request))
    retrieval: RetrievalSnapshot | None = None
    normalized_request_mode = normalize_mode_name(request.mode)

    if normalized_request_mode == "no-skill":
        skills = []
    elif request.skills is not None:
        skills = request.skills
    elif cfg.manager == "direct":
        skills = []
        logger.info("manager=direct: skipping skill discovery, all skills will be copied")
    else:
        if on_event:
            on_event("search_start", {"task": request.task})
        retrieval = _discover_retrieval(
            request.task,
            skill_group=request.skill_group,
            event_callback=on_event,
            max_skills=cfg.max_skills,
        )
        skills = retrieval.selected_skill_ids
        if on_event:
            on_event("search_complete", {"skills": skills, "retrieval": retrieval.metadata})

    if cfg.manager == "direct" and cfg.max_skills:
        logger.warning(
            f"max_skills={cfg.max_skills} is configured but will not be enforced: "
            f"manager=direct copies all skills to the execution environment"
        )

    registry_metadata = _registry_metadata_from_retrieval(cfg, retrieval, request=request)
    decision = kernel.classify(
        request,
        registry_metadata=registry_metadata,
        retrieval=retrieval,
    )
    resolved_mode = decision.mode_decision.mode
    resolved_skills = list(decision.mode_decision.selected_skill_ids or tuple(skills))
    if resolved_mode == "no-skill":
        resolved_skills = []
    allowed_tools = list(request.allowed_tools or decision.mode_decision.allowed_tools or [])
    max_sandbox = decision.mode_decision.max_sandbox
    allow_network = decision.mode_decision.allow_network
    if resolved_mode == "no-skill" and not allowed_tools:
        allowed_tools = list(DEFAULT_BASELINE_TOOLS)

    # 3. Create RunContext
    run_context = RunContext.create(
        task=request.task,
        mode=resolved_mode,
        task_name=request.task_name or None,
        task_id=request.task_id,
        base_dir=request.base_dir or "runs",
    )

    should_copy_all = (
        request.copy_all_skills
        or decision.mode_decision.copy_all_skills
        or (cfg.manager == "direct" and resolved_mode != "no-skill")
    )
    _persist_runtime_snapshots(
        run_context=run_context,
        request=request,
        mode=resolved_mode,
        skills=resolved_skills,
        retrieval=retrieval,
        profile_payload=asdict(decision.profile),
        mode_decision_payload=asdict(decision.mode_decision),
        allowed_tools=allowed_tools or None,
        copy_all_skills=should_copy_all,
    )

    # 4. Build engine via registry
    engine = create_engine(
        resolved_mode,
        run_context=run_context,
        skill_dir=skill_dir,
        allowed_tools=allowed_tools or None,
        max_sandbox=max_sandbox,
        allow_network=allow_network,
    )

    # 5. Build EngineRequest and run
    if request.visualizer:
        visualizer = request.visualizer
    else:
        # Read batch_auto_plan from DAG orchestrator config
        dag_cfg = cfg.orchestrator_config("dag")
        auto_plan = dag_cfg.batch_auto_plan if dag_cfg else 0
        visualizer = NullVisualizer(auto_select_plan=auto_plan)

    engine_request = EngineRequest(
        task=request.task,
        skills=resolved_skills,
        files=request.files,
        visualizer=visualizer,
        copy_all_skills=should_copy_all,
        allowed_tools=allowed_tools or None,
    )

    result = await engine.run(engine_request)
    result.metadata = {
        **result.metadata,
        "run_id": run_context.run_id,
        "requested_mode": request.mode,
        "resolved_mode": resolved_mode,
        "selected_skills": resolved_skills,
        "selected_actions": list(
            result.metadata.get("selected_actions")
            or result.metadata.get("actions_executed")
            or []
        ),
        "feedback_status": result.metadata.get("feedback_status", "not_applicable"),
        "max_sandbox": max_sandbox,
        "allow_network": allow_network,
        "copy_all_skills": should_copy_all,
        "allowed_tools": allowed_tools,
        "environment_profile": asdict(decision.profile),
        "mode_decision": asdict(decision.mode_decision),
        "retrieval": retrieval.to_dict() if retrieval else {},
    }

    # Auto-evaluate if evaluators are configured
    if request.evaluators_config:
        try:
            from .evaluation import evaluate_workspace
            eval_result = await evaluate_workspace(
                evaluators_config=request.evaluators_config,
                aggregation_config=request.aggregation_config,
                workspace_path=run_context.run_dir / "workspace",
                task_id=request.task_id or "",
            )
            if eval_result:
                result.metadata["evaluation"] = eval_result.to_dict()
        except Exception as e:
            logger.warning(f"Evaluation failed for {request.task_id}: {e}")

    _persist_result_envelope(
        run_context=run_context,
        result=result,
        mode=resolved_mode,
        skills=resolved_skills,
    )

    if on_event:
        on_event("execution_complete", {
            "status": result.status,
            "error": result.error,
            "mode": resolved_mode,
            "skills": resolved_skills,
            "run_id": run_context.run_id,
        })

    return result
