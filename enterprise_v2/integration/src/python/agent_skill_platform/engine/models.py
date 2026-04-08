from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


def _coerce_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, tuple):
        return tuple(str(item) for item in value if str(item).strip())
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item).strip())
    return (str(value),)


@dataclass(frozen=True)
class SkillProjection:
    skill_id: str
    display_name: str
    skill_type: str = "script"
    inner_description: str = ""
    outer_description: str = ""
    parameter_schema: dict[str, Any] = field(default_factory=dict)
    default_action_id: str | None = None
    risk_level: str | None = None
    tags: tuple[str, ...] = ()
    version_id: str | None = None
    latest_version_id: str | None = None
    owner: str | None = None
    updated_at: str | None = None
    is_official: bool = False
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SkillProjection":
        metadata = dict(data.get("metadata", {}) or {})
        for key in ("package_root", "install_root", "mounted_path"):
            metadata.pop(key, None)
        return cls(
            skill_id=str(data.get("skill_id", "")).strip(),
            display_name=str(data.get("display_name", "")).strip() or str(data.get("skill_id", "")).strip(),
            skill_type=str(data.get("type", data.get("skill_type", "script"))).strip() or "script",
            inner_description=str(data.get("inner_description", "") or ""),
            outer_description=str(data.get("outer_description", "") or ""),
            parameter_schema=dict(data.get("parameter_schema", {}) or {}),
            default_action_id=data.get("default_action_id"),
            risk_level=data.get("risk_level"),
            tags=_coerce_tuple(data.get("tags", ())),
            version_id=data.get("version_id"),
            latest_version_id=data.get("latest_version_id"),
            owner=data.get("owner"),
            updated_at=data.get("updated_at"),
            is_official=bool(data.get("is_official", False)),
            score=float(data.get("score", 0.0) or 0.0),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "display_name": self.display_name,
            "type": self.skill_type,
            "inner_description": self.inner_description,
            "outer_description": self.outer_description,
            "parameter_schema": dict(self.parameter_schema),
            "default_action_id": self.default_action_id,
            "risk_level": self.risk_level,
            "tags": list(self.tags),
            "version_id": self.version_id,
            "latest_version_id": self.latest_version_id,
            "owner": self.owner,
            "updated_at": self.updated_at,
            "is_official": self.is_official,
            "score": self.score,
            "metadata": dict(self.metadata),
        }

    def with_score(self, score: float) -> "SkillProjection":
        return replace(self, score=float(score))


@dataclass(frozen=True)
class FindSkillRequest:
    query: str = ""
    limit: int = 5
    skill_type: str | None = None
    tags: tuple[str, ...] = ()
    owner: str | None = None
    risk_level: str | None = None
    official_only: bool | None = None
    skill_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> "FindSkillRequest":
        payload = dict(data or {})
        filters = dict(payload.pop("filters", {}) or {})
        payload.update(filters)
        return cls(
            query=str(payload.get("query", "") or ""),
            limit=max(1, int(payload.get("limit", 5) or 5)),
            skill_type=payload.get("skill_type"),
            tags=_coerce_tuple(payload.get("tags", ())),
            owner=payload.get("owner"),
            risk_level=payload.get("risk_level"),
            official_only=payload.get("official_only"),
            skill_ids=_coerce_tuple(payload.get("skill_ids", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "limit": self.limit,
            "skill_type": self.skill_type,
            "tags": list(self.tags),
            "owner": self.owner,
            "risk_level": self.risk_level,
            "official_only": self.official_only,
            "skill_ids": list(self.skill_ids),
        }


@dataclass(frozen=True)
class FindSkillResponse:
    request: FindSkillRequest
    skills: tuple[SkillProjection, ...] = ()
    total_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "total_count": self.total_count,
            "skills": [skill.to_dict() for skill in self.skills],
        }


@dataclass(frozen=True)
class ExecuteSkillRequest:
    skill_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    action_id: str | None = None
    version_id: str | None = None
    trace_id: str | None = None
    environment_profile: str | None = None
    workspace_dir: str | None = None
    run_id: str | None = None
    install_root: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    max_sandbox: str | None = None
    allow_network: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> "ExecuteSkillRequest":
        payload = dict(data or {})
        return cls(
            skill_id=str(payload.get("skill_id", "")).strip(),
            parameters=dict(payload.get("parameters", {}) or {}),
            action_id=payload.get("action_id"),
            version_id=payload.get("version_id"),
            trace_id=payload.get("trace_id"),
            environment_profile=payload.get("environment_profile"),
            workspace_dir=payload.get("workspace_dir"),
            run_id=payload.get("run_id"),
            install_root=payload.get("install_root"),
            env=dict(payload.get("env", {}) or {}),
            max_sandbox=payload.get("max_sandbox"),
            allow_network=bool(payload.get("allow_network", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "parameters": dict(self.parameters),
            "action_id": self.action_id,
            "version_id": self.version_id,
            "trace_id": self.trace_id,
            "environment_profile": self.environment_profile,
            "workspace_dir": self.workspace_dir,
            "run_id": self.run_id,
            "install_root": self.install_root,
            "env": dict(self.env),
            "max_sandbox": self.max_sandbox,
            "allow_network": self.allow_network,
        }


@dataclass(frozen=True)
class RuntimeExecutionResponse:
    run_id: str
    skill_id: str
    version_id: str | None
    action_id: str
    status: str
    summary: str = ""
    resolved_action: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[dict[str, Any], ...] = ()
    feedback: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_runtime_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> "RuntimeExecutionResponse":
        resolved_action = dict(payload.get("resolved_action", {}) or {})
        for key in ("package_root", "install_root", "mounted_path"):
            resolved_action.pop(key, None)
        result = dict(payload.get("result", {}) or {})
        feedback = dict(payload.get("feedback", {}) or {})
        status = str(result.get("status") or feedback.get("status") or ("completed" if feedback.get("success") else "unknown"))
        summary = str(result.get("summary") or feedback.get("summary") or "")
        return cls(
            run_id=str(payload.get("run_id", "") or feedback.get("run_id", "") or ""),
            skill_id=str(result.get("skill_id") or resolved_action.get("skill_id") or feedback.get("skill_id") or ""),
            version_id=resolved_action.get("version_id") or feedback.get("version_id"),
            action_id=str(result.get("action_id") or resolved_action.get("action_id") or feedback.get("action_id") or ""),
            status=status,
            summary=summary,
            resolved_action=resolved_action,
            result=result,
            artifacts=tuple(dict(item) for item in payload.get("artifacts", []) or []),
            feedback=feedback,
            metadata=dict(metadata or {}),
        )

    @property
    def ok(self) -> bool:
        return self.feedback.get("success") if "success" in self.feedback else self.status in {"completed", "partial", "plan_only"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "version_id": self.version_id,
            "action_id": self.action_id,
            "status": self.status,
            "summary": self.summary,
            "resolved_action": dict(self.resolved_action),
            "result": dict(self.result),
            "artifacts": [dict(item) for item in self.artifacts],
            "feedback": dict(self.feedback),
            "metadata": dict(self.metadata),
            "ok": self.ok,
        }


@dataclass(frozen=True)
class ExecuteSkillResponse:
    request: ExecuteSkillRequest
    skill_projection: SkillProjection
    execution: RuntimeExecutionResponse

    @property
    def ok(self) -> bool:
        return self.execution.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "skill_projection": self.skill_projection.to_dict(),
            "execution": self.execution.to_dict(),
            "ok": self.ok,
        }
