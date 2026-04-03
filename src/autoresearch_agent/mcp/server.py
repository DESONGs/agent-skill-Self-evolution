from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from autoresearch_agent.cli.runtime import (
    get_run_artifacts as runtime_get_run_artifacts,
    get_run_status as runtime_get_run_status,
    list_packs,
    project_root_from_input,
    submit_promotion as runtime_submit_promotion,
    validate_project as runtime_validate_project,
)
from autoresearch_agent.core.runtime import RuntimeManager
from autoresearch_agent.mcp.job_store import (
    kill_process,
    load_job,
    process_alive,
    process_start_hint,
    save_job,
    terminate_process,
    update_job,
)


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "autoresearch-agent"
SERVER_VERSION = "0.1.0"
CANCEL_GRACE_SECONDS = max(0.1, float(os.environ.get("AUTORESEARCH_CANCEL_GRACE_SECONDS", "3.0")))

ToolHandler = Callable[[dict[str, Any]], Any]


def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, indent=2) if not isinstance(payload, str) else payload
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload if isinstance(payload, dict) else {"value": payload},
        "isError": is_error,
    }


class ToolInvocationError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"ok": False, "error": {"code": self.code, "message": self.message, "details": self.details}}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _read_message(stream) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            raise ValueError("invalid header line")
        name, value = decoded.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    if content_length <= 0:
        raise ValueError("missing content-length")
    body = stream.read(content_length)
    if not body:
        return None
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request payload must be an object")
    return payload


def _write_message(stream, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


def _subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    source_root = str(Path(__file__).resolve().parents[2])
    existing = env.get("PYTHONPATH", "")
    paths = [entry for entry in existing.split(os.pathsep) if entry]
    if source_root not in paths:
        env["PYTHONPATH"] = os.pathsep.join([source_root, *paths]) if paths else source_root
    return env


class StdioMcpServer:
    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = project_root_from_input(project_root)
        self._initialized = False
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._process_lock = threading.Lock()
        self.tools = self._build_tool_registry()

    def _build_tool_registry(self) -> dict[str, dict[str, Any]]:
        return {
            "ping": {
                "description": "Check that the autoresearch runtime is reachable.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "handler": lambda _args: {"ok": True, "project_root": str(self.project_root)},
            },
            "list_packs": {
                "description": "List bundled research packs.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "handler": lambda _args: {"packs": list_packs()},
            },
            "validate_project": {
                "description": "Validate research.yaml, pack, and dataset for a project root.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "handler": lambda args: runtime_validate_project(args.get("project_root", self.project_root)),
            },
            "run_project": {
                "description": "Submit a local research project run and return a run id for polling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "handler": self._run_project,
            },
            "continue_run": {
                "description": "Submit a continuation run and return the new run id for polling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._continue_run,
            },
            "cancel_run": {
                "description": "Request cancellation for a queued or running run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._cancel_run,
            },
            "stop_run": {
                "description": "Alias of cancel_run for stopping a queued or running run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._cancel_run,
            },
            "get_run_status": {
                "description": "Get status for a previously created run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._get_run_status,
            },
            "list_artifacts": {
                "description": "List artifacts for a previously created run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._list_artifacts,
            },
            "read_artifact": {
                "description": "Read the textual contents of an artifact from a finished run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                        "artifact_path": {"type": "string"},
                        "max_chars": {"type": "integer", "minimum": 1},
                    },
                    "required": ["run_id", "artifact_path"],
                    "additionalProperties": False,
                },
                "handler": self._read_artifact,
            },
            "submit_promotion": {
                "description": "Create a promotion submission bundle for a finished skill lab run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["run_id"],
                    "additionalProperties": False,
                },
                "handler": self._submit_promotion,
            },
        }

    def _set_process(self, run_id: str, process: subprocess.Popen[str] | None) -> None:
        with self._process_lock:
            if process is None:
                self._processes.pop(run_id, None)
                return
            self._processes[run_id] = process

    def _get_process(self, run_id: str) -> subprocess.Popen[str] | None:
        with self._process_lock:
            return self._processes.get(run_id)

    def _job_snapshot(self, project_root: Path, run_id: str) -> dict[str, Any] | None:
        return load_job(project_root, run_id)

    def _spawn_run_process(self, project_root: Path, command: list[str]) -> subprocess.Popen[str]:
        return subprocess.Popen(
            command,
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_subprocess_env(),
            start_new_session=True,
        )

    def _job_response(self, run_id: str, project_root: Path, job: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "run_id": run_id,
            "status": str(job.get("status", "")),
            "project_root": str(job.get("project_root", str(project_root))),
            "parent_run_id": str(job.get("parent_run_id", "")),
            "updated_at": str(job.get("updated_at", "")),
            "error": str(job.get("error", "")),
        }
        for key in ("cancel_requested_at", "terminate_sent_at", "kill_sent_at"):
            value = str(job.get(key, "")).strip()
            if value:
                payload[key] = value
        return payload

    def _maybe_escalate_cancellation(self, project_root: Path, run_id: str, job: dict[str, Any]) -> dict[str, Any]:
        cancel_requested_at = _parse_iso(str(job.get("cancel_requested_at", "")))
        if cancel_requested_at is None:
            return job
        if datetime.now(timezone.utc) < cancel_requested_at + timedelta(seconds=CANCEL_GRACE_SECONDS):
            return job
        if str(job.get("kill_sent_at", "")).strip():
            return job

        pid = int(job.get("pid", 0) or 0)
        pgid = int(job.get("pgid", 0) or 0)
        start_hint = str(job.get("process_start_hint", ""))
        updated_at = _now_iso()
        sent = kill_process(pid, process_group_id=pgid, expected_start_hint=start_hint)
        if not sent:
            return update_job(
                project_root,
                run_id,
                kill_sent_at=updated_at,
                updated_at=updated_at,
                error=str(job.get("error") or "cancel escalation requested but the run process was no longer active"),
            )
        return update_job(project_root, run_id, kill_sent_at=updated_at, updated_at=updated_at)

    def _watch_process(self, project_root: Path, run_id: str) -> None:
        process = self._get_process(run_id)
        if process is None:
            return
        stdout, stderr = process.communicate()
        self._set_process(run_id, None)

        current = self._job_snapshot(project_root, run_id) or {}
        stdout_tail = (stdout or "")[-4000:]
        stderr_tail = (stderr or "")[-4000:]
        updated_at = _now_iso()
        if current.get("status") == "cancelling":
            update_job(
                project_root,
                run_id,
                status="cancelled",
                finished_at=updated_at,
                cancelled_at=updated_at,
                updated_at=updated_at,
                exit_code=process.returncode,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
            )
            return

        if process.returncode == 0:
            update_job(
                project_root,
                run_id,
                status="finished",
                finished_at=updated_at,
                updated_at=updated_at,
                exit_code=0,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
            )
            return

        message = stderr_tail.strip() or stdout_tail.strip() or f"run exited with code {process.returncode}"
        update_job(
            project_root,
            run_id,
            status="failed",
            finished_at=updated_at,
            updated_at=updated_at,
            exit_code=process.returncode,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            error=message,
        )

    def _submit_job(self, project_root: Path, run_id: str, command: list[str], *, parent_run_id: str = "") -> dict[str, Any]:
        existing = self._job_snapshot(project_root, run_id)
        if existing is not None:
            raise ToolInvocationError("run_conflict", f"run already exists: {run_id}", details={"run_id": run_id})

        try:
            RuntimeManager(project_root).get_run(run_id)
        except FileNotFoundError:
            pass
        else:
            raise ToolInvocationError("run_conflict", f"run already exists: {run_id}", details={"run_id": run_id})

        submitted_at = _now_iso()
        save_job(
            project_root,
            run_id,
            {
                "status": "queued",
                "parent_run_id": parent_run_id,
                "submitted_at": submitted_at,
                "updated_at": submitted_at,
                "command": command,
                "error": "",
            },
        )
        process = self._spawn_run_process(project_root, command)
        started_at = _now_iso()
        try:
            pgid = os.getpgid(process.pid)
        except OSError:
            pgid = 0
        current = self._job_snapshot(project_root, run_id) or {}
        initial_status = "cancelling" if str(current.get("status", "")).strip() == "cancelling" else "running"
        job = update_job(
            project_root,
            run_id,
            status=initial_status,
            started_at=started_at,
            updated_at=started_at,
            pid=process.pid,
            pgid=pgid,
            process_start_hint=process_start_hint(process.pid),
        )
        if initial_status == "cancelling":
            if terminate_process(
                process.pid,
                process_group_id=pgid,
                expected_start_hint=str(job.get("process_start_hint", "")),
            ):
                job = update_job(project_root, run_id, terminate_sent_at=started_at, updated_at=started_at)
        self._set_process(run_id, process)
        threading.Thread(target=self._watch_process, args=(project_root, run_id), daemon=True).start()
        response = self._job_response(run_id, project_root, job)
        response["submitted_at"] = submitted_at
        response["started_at"] = started_at
        response["mode"] = "async_poll"
        return response

    def _refresh_job(self, project_root: Path, run_id: str) -> dict[str, Any] | None:
        job = self._job_snapshot(project_root, run_id)
        if job is None:
            return None

        status = str(job.get("status", "")).strip()
        pid = int(job.get("pid", 0) or 0)
        pgid = int(job.get("pgid", 0) or 0)
        start_hint = str(job.get("process_start_hint", ""))
        if status == "cancelling" and pid and process_alive(pid, expected_start_hint=start_hint):
            return self._maybe_escalate_cancellation(project_root, run_id, job)
        if status in {"running", "cancelling"} and pid and not process_alive(pid, expected_start_hint=start_hint):
            try:
                runtime_status = runtime_get_run_status(project_root, run_id)
            except FileNotFoundError:
                updated_at = _now_iso()
                if status == "cancelling":
                    job = update_job(project_root, run_id, status="cancelled", cancelled_at=updated_at, finished_at=updated_at, updated_at=updated_at)
                else:
                    job = update_job(
                        project_root,
                        run_id,
                        status="failed",
                        finished_at=updated_at,
                        updated_at=updated_at,
                        error=str(job.get("error") or "run process ended before writing artifacts"),
                    )
            else:
                job = update_job(
                    project_root,
                    run_id,
                    status=str(runtime_status.get("status", "finished")),
                    finished_at=str(runtime_status.get("updated_at", "")) or _now_iso(),
                    updated_at=str(runtime_status.get("updated_at", "")) or _now_iso(),
                )
        elif status == "cancelling" and not pid and pgid:
            return self._maybe_escalate_cancellation(project_root, run_id, job)
        return job

    def _run_project(self, args: dict[str, Any]) -> Any:
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        run_id = str(args.get("run_id") or "").strip() or _new_run_id()
        command = [sys.executable, "-m", "autoresearch_agent", "run", str(project_root), "--run-id", run_id]
        return self._submit_job(project_root, run_id, command)

    def _continue_run(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        next_run_id = _new_run_id()
        command = [
            sys.executable,
            "-m",
            "autoresearch_agent",
            "continue",
            run_id,
            "--project-root",
            str(project_root),
            "--next-run-id",
            next_run_id,
        ]
        payload = self._submit_job(project_root, next_run_id, command, parent_run_id=run_id)
        payload["parent_run_id"] = run_id
        return payload

    def _cancel_run(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        job = self._refresh_job(project_root, run_id)
        if job is None:
            raise ToolInvocationError("run_not_found", f"run not found: {run_id}", details={"run_id": run_id})

        status = str(job.get("status", "")).strip()
        if status in {"finished", "failed", "cancelled"}:
            return {
                "run_id": run_id,
                "status": status,
                "project_root": str(project_root),
                "updated_at": str(job.get("updated_at", "")),
                "error": str(job.get("error", "")),
            }

        updated_at = _now_iso()
        pid = int(job.get("pid", 0) or 0)
        pgid = int(job.get("pgid", 0) or 0)
        start_hint = str(job.get("process_start_hint", ""))
        job = update_job(project_root, run_id, status="cancelling", updated_at=updated_at, cancel_requested_at=updated_at)
        if pid:
            if terminate_process(pid, process_group_id=pgid, expected_start_hint=start_hint):
                job = update_job(project_root, run_id, terminate_sent_at=updated_at, updated_at=updated_at)
        return self._job_response(run_id, project_root, job)

    def _get_run_status(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        job = self._refresh_job(project_root, run_id)
        if job is not None and str(job.get("status", "")).strip() in {"queued", "running", "failed", "cancelling", "cancelled"}:
            return self._job_response(run_id, project_root, job)
        status = runtime_get_run_status(project_root, run_id)
        if job is None:
            return status
        status["project_root"] = str(job.get("project_root", str(project_root)))
        status["parent_run_id"] = str(job.get("parent_run_id", ""))
        return status

    def _list_artifacts(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        job = self._refresh_job(project_root, run_id)
        if job is not None and str(job.get("status", "")).strip() in {"queued", "running", "cancelling"}:
            return {"run_id": run_id, "status": str(job.get("status", "")), "artifacts": []}
        if job is not None and str(job.get("status", "")).strip() in {"failed", "cancelled"}:
            return {"run_id": run_id, "status": str(job.get("status", "")), "artifacts": [], "error": str(job.get("error", ""))}
        return {"run_id": run_id, "status": "finished", "artifacts": runtime_get_run_artifacts(project_root, run_id)}

    def _read_artifact(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        artifact_path = str(args.get("artifact_path", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        if not artifact_path:
            raise ToolInvocationError("invalid_arguments", "artifact_path is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        job = self._refresh_job(project_root, run_id)
        if job is not None and str(job.get("status", "")).strip() in {"queued", "running", "cancelling"}:
            raise ToolInvocationError("run_in_progress", "run is still in progress", details={"run_id": run_id})
        if job is not None and str(job.get("status", "")).strip() == "failed":
            raise ToolInvocationError("run_failed", str(job.get("error") or "run failed"), details={"run_id": run_id})
        if job is not None and str(job.get("status", "")).strip() == "cancelled":
            raise ToolInvocationError("run_cancelled", "run was cancelled", details={"run_id": run_id})

        run = RuntimeManager(project_root).get_run(run_id)
        artifact = next((item for item in run.artifacts if item["path"] == artifact_path or item["name"] == artifact_path), None)
        if artifact is None:
            raise ToolInvocationError("artifact_not_found", f"artifact not found: {artifact_path}", details={"run_id": run_id, "artifact_path": artifact_path})

        file_path = (run.run_dir / artifact["path"]).resolve()
        run_root = run.run_dir.resolve()
        if file_path != run_root and run_root not in file_path.parents:
            raise ToolInvocationError("invalid_artifact_path", "artifact path escapes run directory", details={"run_id": run_id, "artifact_path": artifact_path})

        raw_text = file_path.read_text(encoding="utf-8")
        max_chars = args.get("max_chars")
        limit = int(max_chars) if isinstance(max_chars, int) and max_chars > 0 else 12000
        content = raw_text[:limit]
        truncated = len(raw_text) > len(content)
        return {
            "run_id": run_id,
            "status": "finished",
            "artifact": {
                "name": artifact["name"],
                "path": artifact["path"],
                "kind": artifact["kind"],
                "size_bytes": artifact["size_bytes"],
                "content": content,
                "truncated": truncated,
            },
        }

    def _submit_promotion(self, args: dict[str, Any]) -> Any:
        run_id = str(args.get("run_id", "")).strip()
        if not run_id:
            raise ToolInvocationError("invalid_arguments", "run_id is required")
        project_root = project_root_from_input(args.get("project_root", self.project_root))
        payload = runtime_submit_promotion(project_root, run_id)
        if isinstance(payload, dict) and "ok" not in payload:
            payload = {"ok": True, **payload}
        return payload

    def _tool_definitions(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = []
        for name, item in self.tools.items():
            definitions.append(
                {
                    "name": name,
                    "description": item["description"],
                    "inputSchema": item["inputSchema"],
                }
            )
        return definitions

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            return _tool_result({"ok": False, "error": {"code": "unknown_tool", "message": f"unknown tool: {name}", "details": {}}}, is_error=True)
        try:
            payload = tool["handler"](arguments)
        except ToolInvocationError as exc:
            return _tool_result(exc.to_payload(), is_error=True)
        except Exception as exc:
            fallback = ToolInvocationError("internal_error", str(exc))
            return _tool_result(fallback.to_payload(), is_error=True)
        if isinstance(payload, dict) and "ok" in payload:
            return _tool_result(payload, is_error=not bool(payload.get("ok", False)))
        return _tool_result({"ok": True, **payload} if isinstance(payload, dict) else payload, is_error=False)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = str(request.get("method", "")).strip()
        if request.get("jsonrpc") != "2.0":
            return _jsonrpc_error(request.get("id"), -32600, "jsonrpc must be '2.0'")

        request_id = request.get("id")
        params = request.get("params", {})
        if not isinstance(params, dict):
            params = {}

        if method in {"notifications/initialized", "initialized"} and request_id is None:
            self._initialized = True
            return None
        if method == "initialize":
            self._initialized = True
            return _jsonrpc_result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                    "instructions": "Use tools/list then tools/call to operate local autoresearch projects.",
                },
            )
        if method == "ping":
            return _jsonrpc_result(request_id, {"ok": True})
        if method in {"tools/list", "tools/call"} and not self._initialized:
            return _jsonrpc_error(request_id, -32002, "initialize must be called before tool requests")
        if method == "tools/list":
            return _jsonrpc_result(request_id, {"tools": self._tool_definitions()})
        if method == "tools/call":
            tool_name = str(params.get("name", "")).strip()
            arguments = params.get("arguments", {})
            if not tool_name:
                return _jsonrpc_error(request_id, -32602, "tool name is required")
            if not isinstance(arguments, dict):
                return _jsonrpc_error(request_id, -32602, "tool arguments must be an object")
            return _jsonrpc_result(request_id, self._call_tool(tool_name, arguments))
        if request_id is None:
            return None
        return _jsonrpc_error(request_id, -32601, f"unsupported method: {method}")


def serve_stdio(project_root: str | Path = ".") -> None:
    server = StdioMcpServer(project_root)
    reader = sys.stdin.buffer
    writer = sys.stdout.buffer
    while True:
        try:
            request = _read_message(reader)
        except Exception as exc:
            response = _jsonrpc_error(None, -32700, f"invalid request: {exc}")
        else:
            if request is None:
                return
            response = server.handle_request(request)
        if response is None:
            continue
        _write_message(writer, response)
