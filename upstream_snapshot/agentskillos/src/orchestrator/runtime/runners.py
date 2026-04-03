"""Runtime action runners.

The resolver decides what to run; these classes perform the actual execution
or a controlled non-shell payload for instruction/mcp/subagent actions.
"""

from __future__ import annotations

import asyncio
import json
import os
import inspect
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from .actions import ActionKind
from .envelope import ArtifactRecord
from .resolve import ActionResolutionError, ResolvedAction


class RunnerExecutionError(RuntimeError):
    """Raised when a runner cannot execute safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_path(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    return value if isinstance(value, Path) else Path(value)


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _parse_stdout_payload(stdout: str) -> Any:
    stripped = stdout.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except Exception:
        return stdout


def _artifacts_from_payload(payload: Any) -> tuple[ArtifactRecord, ...]:
    if not isinstance(payload, Mapping):
        return ()
    raw = payload.get("artifacts")
    if not isinstance(raw, list):
        return ()
    artifacts: list[ArtifactRecord] = []
    for index, item in enumerate(raw):
        if isinstance(item, ArtifactRecord):
            artifacts.append(item)
            continue
        if isinstance(item, Mapping):
            data = dict(item)
            data.setdefault("artifact_id", data.get("id") or f"artifact-{index + 1}")
            data.setdefault("path", data.get("path") or "")
            artifacts.append(ArtifactRecord.from_dict(data))
            continue
        artifacts.append(ArtifactRecord(artifact_id=f"artifact-{index + 1}", path=str(item)))
    return tuple(artifacts)


def _command_for_runtime(runtime: str) -> list[str]:
    runtime = runtime.strip().lower()
    if runtime in {"python", "python3"}:
        return [sys.executable]
    executable = shutil.which(runtime)
    if executable:
        return [executable]
    return [runtime]


@dataclass(frozen=True)
class ActionResult:
    """Execution result emitted by a runner."""

    action_id: str
    skill_id: str
    runner_name: str
    status: str
    summary: str = ""
    payload: Any = None
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    artifacts: tuple[ArtifactRecord, ...] = ()
    started_at: str = field(default_factory=_utc_now)
    completed_at: str = field(default_factory=_utc_now)
    latency_ms: int = 0
    token_usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status in {"completed", "partial", "plan_only"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "skill_id": self.skill_id,
            "runner_name": self.runner_name,
            "status": self.status,
            "summary": self.summary,
            "payload": _jsonable(self.payload),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "token_usage": dict(self.token_usage),
            "metadata": dict(self.metadata),
            "error": self.error,
            "error_code": self.error_code,
        }

    @classmethod
    def success(
        cls,
        *,
        action_id: str,
        skill_id: str,
        runner_name: str,
        summary: str = "",
        payload: Any = None,
        stdout: str = "",
        stderr: str = "",
        return_code: int = 0,
        artifacts: Iterable[ArtifactRecord] | None = None,
        latency_ms: int = 0,
        token_usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ActionResult":
        return cls(
            action_id=action_id,
            skill_id=skill_id,
            runner_name=runner_name,
            status="completed",
            summary=summary,
            payload=payload,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            artifacts=tuple(artifacts or ()),
            completed_at=_utc_now(),
            latency_ms=latency_ms,
            token_usage=dict(token_usage or {}),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failure(
        cls,
        *,
        action_id: str,
        skill_id: str,
        runner_name: str,
        error: str,
        error_code: str | None = None,
        stdout: str = "",
        stderr: str = "",
        return_code: int = 1,
        latency_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> "ActionResult":
        return cls(
            action_id=action_id,
            skill_id=skill_id,
            runner_name=runner_name,
            status="failed",
            error=error,
            error_code=error_code,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            completed_at=_utc_now(),
            latency_ms=latency_ms,
            metadata=dict(metadata or {}),
        )


class ActionRunner(Protocol):
    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult: ...


class InstructionRunner:
    """Return a payload for instruction-only actions without shell execution."""

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        started = time.perf_counter()
        payload = {
            "runner": "instruction",
            "skill_id": action.skill_id,
            "action_id": action.action_id,
            "instruction": action.description or action.runner_config.get("instruction") or "",
            "instruction_prompt": action.description or action.runner_config.get("instruction") or "",
            "input": _jsonable(action_input),
            "workspace_dir": str(_ensure_path(workspace_dir)) if workspace_dir is not None else None,
            "runner_config": dict(action.runner_config),
        }
        return ActionResult.success(
            action_id=action.action_id,
            skill_id=action.skill_id,
            runner_name="instruction",
            summary=action.description or "Instruction action prepared",
            payload=payload,
            latency_ms=int((time.perf_counter() - started) * 1000),
            metadata={"kind": action.kind.value},
        )


class ScriptRunner:
    """Execute a declared script action inside the prepared install."""

    ALLOWED_RUNTIME_NAMES = {"python3", "python", "bash", "sh", "node"}

    def __init__(self, *, allowlist: Iterable[str] | None = None):
        self.allowlist = {item.strip().lower() for item in (allowlist or self.ALLOWED_RUNTIME_NAMES)}

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        started = time.perf_counter()
        runtime = (action.runtime or "").strip().lower()
        if runtime not in self.allowlist:
            raise RunnerExecutionError(
                f"Unsupported script runtime {action.runtime!r}; allowed: {sorted(self.allowlist)}"
            )

        entry_path = action.entry_path
        if entry_path is None:
            raise RunnerExecutionError(f"Script action {action.action_id!r} is missing an entry path")
        if not entry_path.exists():
            raise RunnerExecutionError(f"Script entry does not exist: {entry_path}")

        cwd = _ensure_path(workspace_dir) or action.mounted_path or entry_path.parent
        cwd = cwd.resolve()
        cwd.mkdir(parents=True, exist_ok=True)

        command = _command_for_runtime(runtime)
        command.append(str(entry_path))

        runtime_env = os.environ.copy()
        runtime_env.update({
            "ACTION_ID": action.action_id,
            "SKILL_ID": action.skill_id,
            "WORKSPACE_DIR": str(cwd),
            "INSTALL_ROOT": str(action.install_root) if action.install_root else "",
            "PACKAGE_ROOT": str(action.package_root) if action.package_root else "",
            "ACTION_INPUT_JSON": json.dumps(action_input or {}, ensure_ascii=False),
        })
        if env:
            runtime_env.update({str(key): str(value) for key, value in env.items()})

        timeout_sec = None
        if action.spec is not None and action.spec.timeout_sec is not None:
            timeout_sec = float(action.spec.timeout_sec)

        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=runtime_env,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(json.dumps(action_input or {}, ensure_ascii=False).encode("utf-8")),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError as exc:
                proc.kill()
                await proc.wait()
                raise RunnerExecutionError(
                    f"Script action {action.action_id!r} timed out after {timeout_sec}s"
                ) from exc
        except FileNotFoundError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ActionResult.failure(
                action_id=action.action_id,
                skill_id=action.skill_id,
                runner_name="script",
                error=f"Executable not found for runtime {action.runtime!r}",
                error_code="runtime_not_found",
                latency_ms=latency_ms,
                metadata={"runtime": action.runtime, "entry": str(entry_path)},
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        payload = _parse_stdout_payload(stdout)
        artifacts = _artifacts_from_payload(payload)
        summary = ""
        if isinstance(payload, Mapping):
            summary = str(payload.get("summary") or payload.get("message") or "").strip()
        if not summary:
            summary = stdout.strip().splitlines()[0] if stdout.strip() else ""

        if proc.returncode != 0:
            return ActionResult.failure(
                action_id=action.action_id,
                skill_id=action.skill_id,
                runner_name="script",
                error=stderr.strip() or f"Script exited with status {proc.returncode}",
                error_code="script_failed",
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode,
                latency_ms=latency_ms,
                metadata={
                    "runtime": action.runtime,
                    "command": command,
                    "cwd": str(cwd),
                },
            )

        return ActionResult.success(
            action_id=action.action_id,
            skill_id=action.skill_id,
            runner_name="script",
            summary=summary or f"Script action {action.action_id} completed",
            payload=payload,
            stdout=stdout,
            stderr=stderr,
            return_code=proc.returncode,
            artifacts=artifacts,
            latency_ms=latency_ms,
            metadata={
                "runtime": action.runtime,
                "command": command,
                "cwd": str(cwd),
            },
        )


class McpRunner:
    """Controlled MCP execution wrapper.

    The implementation is intentionally minimal: it validates the declared
    MCP config and returns a structured payload, optionally delegating to an
    injected invoker for test or integration purposes.
    """

    def __init__(self, invoker: Callable[[ResolvedAction, Any], Any] | None = None):
        self.invoker = invoker

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        started = time.perf_counter()
        config = self._require_config(action)
        payload = {
            "runner": "mcp",
            "skill_id": action.skill_id,
            "action_id": action.action_id,
            "server": config["server"],
            "tool": config["tool"],
            "method": config["method"],
            "input": _jsonable(action_input),
            "workspace_dir": str(_ensure_path(workspace_dir)) if workspace_dir is not None else None,
        }
        if self.invoker is not None:
            result = self.invoker(action, action_input)
            if inspect.isawaitable(result):
                result = await result
            payload["result"] = result
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ActionResult.success(
            action_id=action.action_id,
            skill_id=action.skill_id,
            runner_name="mcp",
            summary=f"{config['server']}.{config['tool']} via {config['method']}",
            payload=payload,
            latency_ms=latency_ms,
            metadata={"config": dict(config)},
        )

    def _require_config(self, action: ResolvedAction) -> dict[str, Any]:
        config = dict(action.runner_config)
        missing = [key for key in ("server", "tool", "method") if not config.get(key)]
        if missing:
            raise RunnerExecutionError(
                f"MCP action {action.action_id!r} is missing config keys: {missing}"
            )
        return config


class SubagentRunner:
    """Controlled subagent execution wrapper."""

    def __init__(self, invoker: Callable[[ResolvedAction, Any], Any] | None = None):
        self.invoker = invoker

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        started = time.perf_counter()
        config = self._require_config(action)
        payload = {
            "runner": "subagent",
            "skill_id": action.skill_id,
            "action_id": action.action_id,
            "model": config["model"],
            "allowed_tools": list(config["allowed_tools"]),
            "system_prompt": config["system_prompt"],
            "input": _jsonable(action_input),
            "workspace_dir": str(_ensure_path(workspace_dir)) if workspace_dir is not None else None,
        }
        if self.invoker is not None:
            result = self.invoker(action, action_input)
            if inspect.isawaitable(result):
                result = await result
            payload["result"] = result
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ActionResult.success(
            action_id=action.action_id,
            skill_id=action.skill_id,
            runner_name="subagent",
            summary=f"Subagent {config['model']} executed",
            payload=payload,
            latency_ms=latency_ms,
            metadata={"config": dict(config)},
        )

    def _require_config(self, action: ResolvedAction) -> dict[str, Any]:
        config = dict(action.runner_config)
        missing = [key for key in ("model", "allowed_tools", "system_prompt") if not config.get(key)]
        if missing:
            raise RunnerExecutionError(
                f"Subagent action {action.action_id!r} is missing config keys: {missing}"
            )
        if not isinstance(config.get("allowed_tools"), list):
            raise RunnerExecutionError(
                f"Subagent action {action.action_id!r} allowed_tools must be a list"
            )
        return config


class RunnerRegistry:
    """Registry of runner implementations keyed by action kind."""

    def __init__(
        self,
        *,
        runners: Mapping[str | ActionKind, ActionRunner] | None = None,
        allowlist: Iterable[str] | None = None,
    ):
        self._runners: dict[str, ActionRunner] = {
            ActionKind.INSTRUCTION.value: InstructionRunner(),
            ActionKind.SCRIPT.value: ScriptRunner(allowlist=allowlist),
            ActionKind.MCP.value: McpRunner(),
            ActionKind.SUBAGENT.value: SubagentRunner(),
        }
        if runners:
            for key, runner in runners.items():
                self.register(key, runner)

    def register(self, kind: str | ActionKind, runner: ActionRunner) -> None:
        self._runners[self._key(kind)] = runner

    def get(self, kind: str | ActionKind) -> ActionRunner:
        key = self._key(kind)
        if key not in self._runners:
            raise KeyError(f"Unknown runner kind: {kind!r}")
        return self._runners[key]

    async def run(
        self,
        action: ResolvedAction,
        action_input: Any = None,
        *,
        workspace_dir: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ActionResult:
        runner = self.get(action.kind)
        result = runner.run(action, action_input, workspace_dir=workspace_dir, env=env)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _key(kind: str | ActionKind) -> str:
        return kind.value if isinstance(kind, ActionKind) else str(kind)
