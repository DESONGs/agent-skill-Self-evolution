from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from autoresearch_agent.core.runtime.state_store import atomic_write_json, ensure_dir, read_json


JOB_SCHEMA_VERSION = "mcp_job.v1"


def jobs_root(project_root: str | Path) -> Path:
    root = Path(project_root).resolve() / ".autoresearch" / "state" / "mcp_jobs"
    return ensure_dir(root)


def job_path(project_root: str | Path, run_id: str) -> Path:
    return jobs_root(project_root) / f"{run_id}.json"


def load_job(project_root: str | Path, run_id: str) -> dict[str, Any] | None:
    payload = read_json(job_path(project_root, run_id), None)
    return payload if isinstance(payload, dict) else None


def save_job(project_root: str | Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("schema_version", JOB_SCHEMA_VERSION)
    normalized["run_id"] = run_id
    normalized["project_root"] = str(Path(project_root).resolve())
    atomic_write_json(job_path(project_root, run_id), normalized)
    return normalized


def update_job(project_root: str | Path, run_id: str, **changes: Any) -> dict[str, Any]:
    current = load_job(project_root, run_id) or {"schema_version": JOB_SCHEMA_VERSION, "run_id": run_id}
    current.update(changes)
    return save_job(project_root, run_id, current)


def process_start_hint(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        output = subprocess.check_output(["ps", "-p", str(pid), "-o", "lstart="], text=True)
    except (OSError, subprocess.SubprocessError):
        return ""
    return output.strip()


def process_alive(pid: int, *, expected_start_hint: str = "") -> bool:
    if pid <= 0:
        return False
    if expected_start_hint and process_start_hint(pid) != expected_start_hint:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _signal_process(pid: int, sig: int, *, process_group_id: int = 0, expected_start_hint: str = "") -> bool:
    if not process_alive(pid, expected_start_hint=expected_start_hint):
        return False
    try:
        if process_group_id > 0:
            os.killpg(process_group_id, sig)
        else:
            os.kill(pid, sig)
    except OSError:
        return False
    return True


def terminate_process(pid: int, *, process_group_id: int = 0, expected_start_hint: str = "") -> bool:
    return _signal_process(
        pid,
        signal.SIGTERM,
        process_group_id=process_group_id,
        expected_start_hint=expected_start_hint,
    )


def kill_process(pid: int, *, process_group_id: int = 0, expected_start_hint: str = "") -> bool:
    return _signal_process(
        pid,
        signal.SIGKILL,
        process_group_id=process_group_id,
        expected_start_hint=expected_start_hint,
    )
