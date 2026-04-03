"""Standardized run/result envelope models for runtime execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path_to_str(value: Path | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


@dataclass(frozen=True)
class ArtifactRecord:
    """A normalized artifact emitted by a run."""

    artifact_id: str
    path: str
    kind: str = "file"
    producer: str = ""
    checksum: str | None = None
    size_bytes: int | None = None
    role: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "kind": self.kind,
            "producer": self.producer,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "role": self.role,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRecord":
        return cls(
            artifact_id=str(data.get("artifact_id", "")),
            path=str(data.get("path", "")),
            kind=str(data.get("kind", "file")),
            producer=str(data.get("producer", "")),
            checksum=data.get("checksum"),
            size_bytes=data.get("size_bytes"),
            role=str(data.get("role", "")),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class RunEnvelope:
    """Runtime state for a single execution."""

    run_id: str
    task: str
    mode: str
    skill_group: str = ""
    selected_skills: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    allowed_tools: list[str] | None = None
    copy_all_skills: bool = False
    run_dir: Path | None = None
    exec_dir: Path | None = None
    workspace_dir: Path | None = None
    logs_dir: Path | None = None
    skills_dir: Path | None = None
    created_at: str = field(default_factory=_utc_now)
    environment: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=dict)
    installs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "mode": self.mode,
            "skill_group": self.skill_group,
            "selected_skills": list(self.selected_skills),
            "files": list(self.files),
            "allowed_tools": list(self.allowed_tools) if self.allowed_tools is not None else None,
            "copy_all_skills": self.copy_all_skills,
            "run_dir": _path_to_str(self.run_dir),
            "exec_dir": _path_to_str(self.exec_dir),
            "workspace_dir": _path_to_str(self.workspace_dir),
            "logs_dir": _path_to_str(self.logs_dir),
            "skills_dir": _path_to_str(self.skills_dir),
            "created_at": self.created_at,
            "environment": dict(self.environment),
            "retrieval": dict(self.retrieval),
            "installs": list(self.installs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunEnvelope":
        return cls(
            run_id=str(data.get("run_id", "")),
            task=str(data.get("task", "")),
            mode=str(data.get("mode", "")),
            skill_group=str(data.get("skill_group", "")),
            selected_skills=list(data.get("selected_skills", []) or []),
            files=list(data.get("files", []) or []),
            allowed_tools=data.get("allowed_tools"),
            copy_all_skills=bool(data.get("copy_all_skills", False)),
            run_dir=Path(data["run_dir"]) if data.get("run_dir") else None,
            exec_dir=Path(data["exec_dir"]) if data.get("exec_dir") else None,
            workspace_dir=Path(data["workspace_dir"]) if data.get("workspace_dir") else None,
            logs_dir=Path(data["logs_dir"]) if data.get("logs_dir") else None,
            skills_dir=Path(data["skills_dir"]) if data.get("skills_dir") else None,
            created_at=str(data.get("created_at", _utc_now())),
            environment=dict(data.get("environment", {}) or {}),
            retrieval=dict(data.get("retrieval", {}) or {}),
            installs=list(data.get("installs", []) or []),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class ResultEnvelope:
    """Normalized run result emitted after execution."""

    run_id: str
    status: str
    summary: str = ""
    error: Optional[str] = None
    mode: str = ""
    started_at: str = field(default_factory=_utc_now)
    completed_at: str | None = None
    selected_skills: list[str] = field(default_factory=list)
    actions_executed: list[str] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status in {"completed", "partial", "plan_only"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "summary": self.summary,
            "error": self.error,
            "mode": self.mode,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "selected_skills": list(self.selected_skills),
            "actions_executed": list(self.actions_executed),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResultEnvelope":
        return cls(
            run_id=str(data.get("run_id", "")),
            status=str(data.get("status", "")),
            summary=str(data.get("summary", "")),
            error=data.get("error"),
            mode=str(data.get("mode", "")),
            started_at=str(data.get("started_at", _utc_now())),
            completed_at=data.get("completed_at"),
            selected_skills=list(data.get("selected_skills", []) or []),
            actions_executed=list(data.get("actions_executed", []) or []),
            artifacts=[ArtifactRecord.from_dict(item) for item in data.get("artifacts", []) or []],
            metrics=dict(data.get("metrics", {}) or {}),
            metadata=dict(data.get("metadata", {}) or {}),
        )

    @classmethod
    def success(
        cls,
        *,
        run_id: str,
        summary: str = "",
        mode: str = "",
        selected_skills: list[str] | None = None,
        actions_executed: list[str] | None = None,
        artifacts: list[ArtifactRecord] | None = None,
        metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ResultEnvelope":
        return cls(
            run_id=run_id,
            status="completed",
            summary=summary,
            mode=mode,
            completed_at=_utc_now(),
            selected_skills=list(selected_skills or []),
            actions_executed=list(actions_executed or []),
            artifacts=list(artifacts or []),
            metrics=dict(metrics or {}),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failure(
        cls,
        *,
        run_id: str,
        error: str,
        mode: str = "",
        summary: str = "",
        selected_skills: list[str] | None = None,
        actions_executed: list[str] | None = None,
        artifacts: list[ArtifactRecord] | None = None,
        metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ResultEnvelope":
        return cls(
            run_id=run_id,
            status="failed",
            summary=summary,
            error=error,
            mode=mode,
            completed_at=_utc_now(),
            selected_skills=list(selected_skills or []),
            actions_executed=list(actions_executed or []),
            artifacts=list(artifacts or []),
            metrics=dict(metrics or {}),
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class RunFeedbackEnvelope:
    """Append-only runtime feedback emitted after action execution."""

    run_id: str
    mode: str
    skill_id: str
    version_id: str | None
    action_id: str
    success: bool
    latency_ms: int = 0
    token_usage: dict[str, Any] = field(default_factory=dict)
    artifact_count: int = 0
    error_code: str | None = None
    layer_source: str = "active"
    feedback_source: str = "RUNTIME"
    feedback_type: str = "EXECUTION"
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "skill_id": self.skill_id,
            "version_id": self.version_id,
            "action_id": self.action_id,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "token_usage": dict(self.token_usage),
            "artifact_count": self.artifact_count,
            "error_code": self.error_code,
            "layer_source": self.layer_source,
            "feedback_source": self.feedback_source,
            "feedback_type": self.feedback_type,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunFeedbackEnvelope":
        return cls(
            run_id=str(data.get("run_id", "")),
            mode=str(data.get("mode", "")),
            skill_id=str(data.get("skill_id", "")),
            version_id=data.get("version_id"),
            action_id=str(data.get("action_id", "")),
            success=bool(data.get("success", False)),
            latency_ms=int(data.get("latency_ms", 0) or 0),
            token_usage=dict(data.get("token_usage", {}) or {}),
            artifact_count=int(data.get("artifact_count", 0) or 0),
            error_code=data.get("error_code"),
            layer_source=str(data.get("layer_source", "active")),
            feedback_source=str(data.get("feedback_source", "RUNTIME")),
            feedback_type=str(data.get("feedback_type", "EXECUTION")),
            created_at=str(data.get("created_at", _utc_now())),
            metadata=dict(data.get("metadata", {}) or {}),
        )

    @classmethod
    def from_action_result(
        cls,
        *,
        run_id: str,
        mode: str,
        layer_source: str,
        resolved_action: Any,
        result: Any,
        metadata: dict[str, Any] | None = None,
    ) -> "RunFeedbackEnvelope":
        token_usage = dict(getattr(result, "token_usage", {}) or {})
        result_metadata = dict(getattr(result, "metadata", {}) or {})
        if not token_usage and isinstance(result_metadata.get("token_usage"), dict):
            token_usage = dict(result_metadata["token_usage"])

        return cls(
            run_id=run_id,
            mode=mode,
            skill_id=str(getattr(resolved_action, "skill_id", "")),
            version_id=getattr(resolved_action, "version_id", None),
            action_id=str(getattr(resolved_action, "action_id", "")),
            success=bool(getattr(result, "is_success", False)),
            latency_ms=int(getattr(result, "latency_ms", 0) or 0),
            token_usage=token_usage,
            artifact_count=len(getattr(result, "artifacts", ()) or ()),
            error_code=getattr(result, "error_code", None) or result_metadata.get("error_code"),
            layer_source=layer_source,
            metadata=dict(metadata or {}),
        )
