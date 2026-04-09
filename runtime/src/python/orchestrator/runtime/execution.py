"""Shared runtime execution helpers for action-driven engines."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from .envelope import ArtifactRecord


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from raw model output."""
    if not text:
        return None

    fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        try:
            payload = json.loads(fenced.group(1))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return payload

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            payload = json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return payload
    return None


def extract_execution_summary(text: str) -> tuple[str, bool]:
    """Extract execution summary and success state from a standard response."""
    if not text:
        return "", True

    match = re.search(
        r"<execution_summary>(.*?)</execution_summary>",
        text,
        re.DOTALL,
    )
    if not match:
        stripped = text.strip()
        return stripped, True if stripped else True

    summary = match.group(1).strip()
    status_match = re.search(r"STATUS:\s*(SUCCESS|FAILURE)", summary, re.IGNORECASE)
    if not status_match:
        return summary, True
    return summary, status_match.group(1).upper() == "SUCCESS"


def build_action_catalog(installs: list[Any]) -> list[dict[str, Any]]:
    """Build a transport-safe action catalog from hydrated installs."""
    catalog: list[dict[str, Any]] = []
    for install in installs:
        bundle = getattr(getattr(install, "package", None), "bundle", None)
        manifest = getattr(install, "action_manifest", None)
        if manifest is None or bundle is None:
            continue

        for action in manifest.actions:
            entry = {
                "skill_id": bundle.skill_id,
                "version_id": bundle.version_id,
                "action_id": action.id,
                "kind": action.kind.value,
                "description": action.description,
                "default": bundle.default_action == action.id,
                "entry": action.entry,
                "runtime": action.runtime,
                "timeout_sec": action.timeout_sec,
                "input_schema": action.input_schema,
                "output_schema": action.output_schema,
                "side_effects": list(action.side_effects),
                "idempotency": action.idempotency,
                "sandbox": action.sandbox,
                "allow_network": action.allow_network,
            }
            if action.mcp is not None:
                entry["mcp"] = dict(action.mcp)
            if action.subagent is not None:
                entry["subagent"] = dict(action.subagent)
            catalog.append(entry)
    return catalog


def scan_workspace_artifacts(
    workspace_dir: Path,
    *,
    producer: str = "",
    role: str = "",
) -> list[ArtifactRecord]:
    """Scan a workspace and normalize file artifacts."""
    if not workspace_dir.exists():
        return []

    artifacts: list[ArtifactRecord] = []
    for path in sorted(p for p in workspace_dir.rglob("*") if p.is_file()):
        rel_path = path.relative_to(workspace_dir).as_posix()
        digest = sha256(path.read_bytes()).hexdigest()
        artifacts.append(
            ArtifactRecord(
                artifact_id=rel_path,
                path=f"workspace/{rel_path}",
                producer=producer,
                checksum=digest,
                size_bytes=path.stat().st_size,
                role=role,
            )
        )
    return artifacts


def summarize_action_results(action_results: list[dict[str, Any]]) -> str:
    """Build a concise summary from executed actions."""
    if not action_results:
        return ""
    completed = [item for item in action_results if item.get("status") == "completed"]
    failed = [item for item in action_results if item.get("status") == "failed"]
    if failed:
        first = failed[0]
        return first.get("summary") or first.get("error") or "Action execution failed"
    if completed:
        return completed[-1].get("summary", "")
    return ""
