"""Typed contracts for the Environment Kernel slice.

These are intentionally small and transport-friendly so the runtime can derive
mode decisions without importing manager/orchestrator internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

AUTO_MODE_NAMES = {"", "auto", "auto-selected", "auto_selected", "derived", None}
CONCRETE_MODE_ALIASES = {
    "baseline": "no-skill",
    "direct": "no-skill",
    "no_skill": "no-skill",
    "free_style": "free-style",
}
VALID_MODES = {"no-skill", "free-style", "dag"}


def normalize_mode_name(mode: str | None) -> str:
    """Normalize user-facing mode strings to the canonical runtime names."""

    if mode in AUTO_MODE_NAMES:
        return "auto"

    normalized = str(mode).strip().lower().replace("_", "-")
    return CONCRETE_MODE_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class SkillCandidate:
    """Minimal skill metadata needed by the kernel."""

    skill_id: str
    score: float = 0.0
    source_layer: str = "active"
    requires_dag: bool = False
    action_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "score": self.score,
            "source_layer": self.source_layer,
            "requires_dag": self.requires_dag,
            "action_count": self.action_count,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RetrievalSnapshot:
    """Normalized retrieval output used for mode selection."""

    query: str
    candidates: tuple[SkillCandidate, ...] = ()
    dormant_suggestions: tuple[SkillCandidate, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def selected_skill_ids(self) -> list[str]:
        return [candidate.skill_id for candidate in self.candidates]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "dormant_suggestions": [
                candidate.to_dict() for candidate in self.dormant_suggestions
            ],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EnvironmentRuntimeDefaults:
    """Runtime defaults normally supplied by config."""

    manager_name: str = "tree"
    orchestrator_name: str = "dag"
    skill_group: str = "skill_seeds"
    max_skills: int = 10
    layering_mode: str = "disabled"
    execution_timeout: float | None = None
    default_allowed_tools: tuple[str, ...] = ()
    max_sandbox: str = "workspace-write"
    allow_network: bool = False


@dataclass(frozen=True)
class TaskContext:
    """Task-facing request input after extracting a TaskRequest-like object."""

    task: str
    mode: str = "auto"
    skill_group: str = "skill_seeds"
    selected_skill_ids: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    copy_all_skills: bool = False
    allowed_tools: tuple[str, ...] | None = None
    max_sandbox: str | None = None
    allow_network: bool | None = None


@dataclass(frozen=True)
class ModeDecision:
    """Explicit choice of execution mode."""

    mode: str
    rationale: str
    selected_skill_ids: tuple[str, ...] = ()
    copy_all_skills: bool = False
    allowed_tools: tuple[str, ...] | None = None
    max_sandbox: str = "workspace-write"
    allow_network: bool = False


@dataclass(frozen=True)
class EnvironmentProfile:
    """Environment classification for the runtime chain."""

    task: str
    request_mode: str
    effective_mode: str
    mode_source: str
    skill_group: str
    manager_name: str
    orchestrator_name: str
    selected_skill_ids: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    copy_all_skills: bool = False
    allowed_tools: tuple[str, ...] | None = None
    layering_mode: str = "disabled"
    execution_timeout: float | None = None
    max_sandbox: str = "workspace-write"
    allow_network: bool = False
    retrieval_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnvironmentDecision:
    """Combined output of profile building and mode selection."""

    profile: EnvironmentProfile
    mode_decision: ModeDecision
    retrieval: RetrievalSnapshot | None = None


def _as_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, tuple):
        return tuple(str(item) for item in values)
    if isinstance(values, list):
        return tuple(str(item) for item in values)
    return (str(values),)


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def extract_task_context(request: Any) -> TaskContext:
    """Extract a TaskContext from a TaskRequest-like object or mapping."""

    if isinstance(request, Mapping):
        getter = request.get
    else:
        getter = lambda key, default=None: getattr(request, key, default)

    return TaskContext(
        task=str(getter("task", "")),
        mode=normalize_mode_name(getter("mode", "auto")),
        skill_group=str(getter("skill_group", "skill_seeds")),
        selected_skill_ids=_as_tuple(getter("skills", None)),
        file_paths=_as_tuple(getter("files", None)),
        copy_all_skills=bool(getter("copy_all_skills", False)),
        allowed_tools=_as_tuple(getter("allowed_tools", None)) or None,
        max_sandbox=(
            str(getter("max_sandbox")).strip()
            if getter("max_sandbox", None) is not None
            else None
        ),
        allow_network=_as_optional_bool(getter("allow_network", None)),
    )
