from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path
from dataclasses import replace

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from orchestrator.runtime.dispatcher import SkillRuntimeDispatcher
from orchestrator.runtime.envelope import RunFeedbackEnvelope
from orchestrator.runtime.executors.agent_executor import AgentExecutor
from orchestrator.runtime.install import RuntimeInstallBundle, hydrate_skill_install
from orchestrator.runtime.resolve import ActionResolver
from orchestrator.runtime.runners import ActionResult, RunnerExecutionError

import orchestrator.runtime.executors.agent_executor as agent_executor_mod


def _copy_package_with_skill_type(tmp_path: Path, skill_type: str) -> Path:
    source = ROOT / "tests" / "fixtures" / "valid_skill_package"
    target = tmp_path / f"package-{skill_type}"
    shutil.copytree(source, target)

    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["type"] = skill_type
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _copy_package_with_single_action(tmp_path: Path, skill_type: str = "agent") -> Path:
    package_root = _copy_package_with_skill_type(tmp_path, skill_type)
    actions_path = package_root / "actions.yaml"
    manifest = yaml.safe_load(actions_path.read_text(encoding="utf-8"))
    manifest["actions"] = manifest["actions"][:1]
    actions_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return package_root


class RecordingRunnerRegistry:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def run(self, action, action_input=None, *, workspace_dir=None, env=None):
        payload = dict(action_input or {}) if isinstance(action_input, dict) else {"value": action_input}
        self.calls.append((action.action_id, payload))
        return ActionResult.success(
            action_id=action.action_id,
            skill_id=action.skill_id,
            runner_name=action.runner_name,
            summary=f"{action.action_id} complete",
            payload={"received": payload},
            metadata={"runner_kind": action.kind.value},
        )


class ForbiddenPlannerClient:
    def __init__(self, *args, **kwargs):
        raise AssertionError("planner client should not be instantiated for single-action skills")


class FakePlannerClient:
    responses: list[str] = []
    instances: list["FakePlannerClient"] = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.prompts: list[str] = []
        FakePlannerClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not FakePlannerClient.responses:
            raise AssertionError("planner client ran out of scripted responses")
        return FakePlannerClient.responses.pop(0)


def test_build_install_bundle_defaults_to_script_skill_type() -> None:
    package_root = ROOT / "tests" / "fixtures" / "valid_skill_package"

    bundle = RuntimeInstallBundle.from_package_root(package_root)

    assert bundle.skill_type == "script"
    assert bundle.to_dict()["skill_type"] == "script"


def test_run_runtime_dispatches_agent_skill_type(tmp_path: Path) -> None:
    package_root = _copy_package_with_single_action(tmp_path, "agent")

    bundle = RuntimeInstallBundle.from_package_root(package_root)
    assert bundle.skill_type == "agent"

    install = hydrate_skill_install(package_root, install_root=tmp_path / "installs")
    action = ActionResolver().resolve_install(install)
    payload = asyncio.run(SkillRuntimeDispatcher().run(action, {"task": "review-pr"}))

    assert action.skill_type == "agent"
    assert payload.metadata["skill_type"] == "agent"
    assert payload.metadata["executor"] == "agent"
    assert payload.metadata["tool_surface"] == ["read_file", "run_action"]

    feedback = RunFeedbackEnvelope.from_action_result(
        run_id="run-1",
        mode="direct",
        layer_source="active",
        resolved_action=action,
        result=payload,
        metadata={"workspace_dir": "x"},
    )
    assert feedback.metadata["skill_type"] == "agent"
    assert feedback.metadata["executor"] == "agent"
    assert feedback.metadata["tool_surface"] == ["read_file", "run_action"]


def test_run_runtime_uses_single_action_fast_path_without_planner(tmp_path: Path, monkeypatch) -> None:
    package_root = _copy_package_with_single_action(tmp_path, "agent")
    install = hydrate_skill_install(package_root, install_root=tmp_path / "installs")
    action = ActionResolver().resolve_install(install)

    monkeypatch.setattr(agent_executor_mod, "SkillClient", ForbiddenPlannerClient)

    registry = RecordingRunnerRegistry()
    dispatcher = SkillRuntimeDispatcher(registry)
    payload = asyncio.run(dispatcher.run(action, {"task": "summarize"}))

    assert registry.calls == [("run", {"task": "summarize"})]
    assert payload.metadata["planner_used"] is False
    assert payload.metadata["planner_steps"] == 1
    assert len(payload.metadata["planner_trace"]) == 1
    assert payload.metadata["tool_surface"] == ["read_file", "run_action"]
    assert payload.metadata["allowed_tools"] == ["read_file", "run_action"]
    assert payload.metadata["profile"]["policy"]["max_steps"] == 6

    feedback = RunFeedbackEnvelope.from_action_result(
        run_id="run-fast-path",
        mode="direct",
        layer_source="active",
        resolved_action=action,
        result=payload,
        metadata={"workspace_dir": "x"},
    )
    assert feedback.metadata["planner_used"] is False
    assert feedback.metadata["planner_steps"] == 1


def test_run_runtime_dispatches_ai_decision_skill_type(tmp_path: Path) -> None:
    package_root = _copy_package_with_single_action(tmp_path, "ai_decision")

    bundle = RuntimeInstallBundle.from_package_root(package_root)
    assert bundle.skill_type == "ai_decision"

    install = hydrate_skill_install(package_root, install_root=tmp_path / "installs")
    action = ActionResolver().resolve_install(install)
    payload = asyncio.run(SkillRuntimeDispatcher().run(action, {"task": "review-pr"}))

    assert action.kind.value == "script"
    assert action.skill_type == "ai_decision"
    assert payload.metadata["skill_type"] == "ai_decision"
    assert payload.metadata["executor"] == "agent"
    assert payload.metadata["tool_surface"] == ["read_file", "run_action"]
    assert payload.metadata["allowed_tools"] == ["read_file", "run_action"]
    assert payload.metadata["profile"]["policy"]["max_steps"] == 3
    assert payload.metadata["planner_used"] is False

    feedback = RunFeedbackEnvelope.from_action_result(
        run_id="run-2",
        mode="direct",
        layer_source="active",
        resolved_action=action,
        result=payload,
        metadata={"workspace_dir": "x"},
    )
    assert feedback.metadata["skill_type"] == "ai_decision"
    assert feedback.metadata["executor"] == "agent"
    assert feedback.metadata["tool_surface"] == ["read_file", "run_action"]


def test_run_runtime_performs_bounded_multi_step_planning(tmp_path: Path, monkeypatch) -> None:
    package_root = _copy_package_with_skill_type(tmp_path, "agent")
    install = hydrate_skill_install(package_root, install_root=tmp_path / "installs")
    action = ActionResolver().resolve_install(install)

    FakePlannerClient.responses = [
        json.dumps(
            {
                "status": "select",
                "skill_id": action.skill_id,
                "action_id": "validate",
                "input": {"task": "follow-up"},
                "summary": "validate after run",
            }
        ),
        json.dumps(
            {
                "status": "finish",
                "summary": "done",
            }
        ),
    ]
    FakePlannerClient.instances = []
    monkeypatch.setattr(agent_executor_mod, "SkillClient", FakePlannerClient)

    registry = RecordingRunnerRegistry()
    dispatcher = SkillRuntimeDispatcher(registry)
    payload = asyncio.run(dispatcher.run(action, {"task": "review-pr"}))

    assert registry.calls == [
        ("run", {"task": "review-pr"}),
        ("validate", {"task": "follow-up"}),
    ]
    assert payload.metadata["planner_used"] is True
    assert payload.metadata["planner_steps"] == 2
    assert len(payload.metadata["planner_trace"]) == 3
    assert payload.metadata["planner_trace"][0]["decision"]["action_id"] == "run"
    assert payload.metadata["planner_trace"][-1]["decision"]["status"] == "finish"
    assert payload.metadata["profile"]["policy"]["max_steps"] == 6
    assert payload.metadata["tool_surface"] == ["read_file", "run_action"]
    assert len(FakePlannerClient.instances) == 1
    assert len(FakePlannerClient.instances[0].prompts) == 2

    feedback = RunFeedbackEnvelope.from_action_result(
        run_id="run-multi-step",
        mode="direct",
        layer_source="active",
        resolved_action=action,
        result=payload,
        metadata={"workspace_dir": "x"},
    )
    assert feedback.metadata["planner_used"] is True
    assert feedback.metadata["planner_steps"] == 2
    assert feedback.metadata["planner_trace"][-1]["decision"]["status"] == "finish"


def test_run_action_rejects_catalog_outside_declared_actions(tmp_path: Path) -> None:
    package_root = _copy_package_with_skill_type(tmp_path, "agent")
    install = hydrate_skill_install(package_root, install_root=tmp_path / "installs")
    action = ActionResolver().resolve_install(install)
    tampered = replace(action, action_catalog=(action.action_catalog[0],))

    executor = AgentExecutor(RecordingRunnerRegistry())

    try:
        asyncio.run(executor.run_action("validate", {}, action=tampered))
    except RunnerExecutionError as exc:
        assert "is not declared" in str(exc)
    else:
        raise AssertionError("expected RunnerExecutionError for out-of-catalog action")
