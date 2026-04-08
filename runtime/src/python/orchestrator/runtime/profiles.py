from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class SkillType(str, Enum):
    SCRIPT = "script"
    AGENT = "agent"
    AI_DECISION = "ai_decision"


def normalize_skill_type(value: Any | None, *, default: str = SkillType.SCRIPT.value) -> str:
    raw = default if value is None else str(value).strip().lower()
    if not raw:
        return default
    try:
        return SkillType(raw).value
    except ValueError as exc:
        raise ValueError(f"Unsupported skill type: {value!r}") from exc


def infer_skill_type(manifest_payload: Mapping[str, Any] | None, action_kinds: Iterable[Any]) -> str:
    payload = dict(manifest_payload or {})
    explicit = payload.get("skill_type") or payload.get("type")
    if explicit is not None:
        return normalize_skill_type(explicit)

    normalized_kinds: list[str] = []
    for kind in action_kinds:
        value = getattr(kind, "kind", kind)
        value = getattr(value, "value", value)
        normalized = str(value).strip().lower()
        if normalized:
            normalized_kinds.append(normalized)
    if any(kind != "script" for kind in normalized_kinds):
        return SkillType.AGENT.value
    return SkillType.SCRIPT.value


@dataclass(frozen=True)
class SkillExecutionProfile:
    skill_type: str
    executor_name: str
    allowed_tools: tuple[str, ...] = ()
    description: str = ""
    policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_type": self.skill_type,
            "executor_name": self.executor_name,
            "allowed_tools": list(self.allowed_tools),
            "description": self.description,
            "policy": dict(self.policy),
        }


def profile_for_skill_type(skill_type: Any) -> SkillExecutionProfile:
    normalized = normalize_skill_type(skill_type)
    if normalized == SkillType.SCRIPT.value:
        return SkillExecutionProfile(
            skill_type=normalized,
            executor_name="script",
            allowed_tools=(),
            description="Contract-driven script execution profile.",
            policy={
                "mode": "direct",
                "max_steps": 1,
                "tool_surface": [],
            },
        )
    if normalized == SkillType.AI_DECISION.value:
        return SkillExecutionProfile(
            skill_type=normalized,
            executor_name="agent",
            allowed_tools=("read_file", "run_action"),
            description="Decision-oriented agent profile that uses a constrained tool surface.",
            policy={
                "mode": "decision",
                "requires_explicit_action": True,
                "max_steps": 3,
                "tool_surface": ["read_file", "run_action"],
            },
        )
    return SkillExecutionProfile(
        skill_type=normalized,
        executor_name="agent",
        allowed_tools=("read_file", "run_action"),
        description="Bounded agent profile with explicit tool routing.",
        policy={
            "mode": "agent",
            "requires_explicit_action": True,
            "max_steps": 6,
            "tool_surface": ["read_file", "run_action"],
        },
    )
