"""Action contract models and parsers for ``actions.yaml``.

This module keeps the runtime-facing action types stable while delegating raw
``actions.yaml`` parsing to ``skill_contract``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from skill_contract.parsers.actions import load_actions_mapping


class ActionContractError(ValueError):
    """Raised when an action manifest fails validation."""


class ActionKind(str, Enum):
    """Supported action kinds declared in ``actions.yaml``."""

    SCRIPT = "script"
    MCP = "mcp"
    INSTRUCTION = "instruction"
    SUBAGENT = "subagent"


@dataclass(frozen=True)
class ActionSpec:
    """Typed declaration of a single executable action."""

    id: str
    kind: ActionKind
    entry: Optional[str] = None
    runtime: Optional[str] = None
    timeout_sec: Optional[float] = None
    sandbox: Optional[str] = None
    allow_network: bool = False
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)
    idempotency: str = "best_effort"
    telemetry: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    mcp: dict[str, Any] | None = None
    subagent: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionSpec":
        kind_value = data.get("kind")
        try:
            kind = ActionKind(kind_value)
        except Exception as exc:
            raise ActionContractError(f"Unsupported action kind: {kind_value!r}") from exc

        input_schema = data.get("input_schema") or {}
        output_schema = data.get("output_schema") or {}
        if not isinstance(input_schema, dict):
            raise ActionContractError(f"Action {data.get('id')!r} input_schema must be a mapping")
        if not isinstance(output_schema, dict):
            raise ActionContractError(f"Action {data.get('id')!r} output_schema must be a mapping")

        side_effects = data.get("side_effects") or []
        if not isinstance(side_effects, list) or any(not isinstance(item, str) for item in side_effects):
            raise ActionContractError(f"Action {data.get('id')!r} side_effects must be a list[str]")

        telemetry = data.get("telemetry") or {}
        if not isinstance(telemetry, dict):
            raise ActionContractError(f"Action {data.get('id')!r} telemetry must be a mapping")

        mcp = data.get("mcp")
        if mcp is not None and not isinstance(mcp, dict):
            raise ActionContractError(f"Action {data.get('id')!r} mcp must be a mapping")

        subagent = data.get("subagent")
        if subagent is not None and not isinstance(subagent, dict):
            raise ActionContractError(f"Action {data.get('id')!r} subagent must be a mapping")

        timeout_sec = data.get("timeout_sec")
        if timeout_sec is not None:
            timeout_sec = float(timeout_sec)
            if timeout_sec < 0:
                raise ActionContractError(f"Action {data.get('id')!r} timeout_sec must be non-negative")

        allow_network = bool(data.get("allow_network", False))
        idempotency = data.get("idempotency", "best_effort")
        if idempotency not in {"exact", "best_effort", "none"}:
            raise ActionContractError(f"Action {data.get('id')!r} has invalid idempotency: {idempotency!r}")

        return cls(
            id=str(data.get("id", "")).strip(),
            kind=kind,
            entry=data.get("entry"),
            runtime=data.get("runtime"),
            timeout_sec=timeout_sec,
            sandbox=data.get("sandbox"),
            allow_network=allow_network,
            input_schema=input_schema,
            output_schema=output_schema,
            side_effects=side_effects,
            idempotency=idempotency,
            telemetry=telemetry,
            description=str(data.get("description", "")),
            mcp=dict(mcp) if mcp is not None else None,
            subagent=dict(subagent) if subagent is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value,
            "allow_network": self.allow_network,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "side_effects": list(self.side_effects),
            "idempotency": self.idempotency,
            "telemetry": dict(self.telemetry),
            "description": self.description,
        }
        if self.entry is not None:
            result["entry"] = self.entry
        if self.runtime is not None:
            result["runtime"] = self.runtime
        if self.timeout_sec is not None:
            result["timeout_sec"] = self.timeout_sec
        if self.sandbox is not None:
            result["sandbox"] = self.sandbox
        if self.mcp is not None:
            result["mcp"] = dict(self.mcp)
        if self.subagent is not None:
            result["subagent"] = dict(self.subagent)
        return result

    def validate(self, package_root: Path | None = None) -> None:
        if not self.id:
            raise ActionContractError("Action id must be non-empty")
        if self.kind == ActionKind.SCRIPT and not self.entry:
            raise ActionContractError(f"Action {self.id!r} requires an entry path")
        if self.kind == ActionKind.MCP:
            if self.mcp is None:
                raise ActionContractError(f"Action {self.id!r} requires an mcp config block")
            missing = [key for key in ("server", "tool", "method") if not str(self.mcp.get(key, "")).strip()]
            if missing:
                raise ActionContractError(
                    f"Action {self.id!r} mcp config missing required fields: {', '.join(missing)}"
                )
        if self.kind == ActionKind.SUBAGENT:
            if self.subagent is None:
                raise ActionContractError(f"Action {self.id!r} requires a subagent config block")
            missing = [key for key in ("model", "system_prompt") if not str(self.subagent.get(key, "")).strip()]
            if missing:
                raise ActionContractError(
                    f"Action {self.id!r} subagent config missing required fields: {', '.join(missing)}"
                )
            allowed_tools = self.subagent.get("allowed_tools", [])
            if not isinstance(allowed_tools, list) or any(not isinstance(item, str) for item in allowed_tools):
                raise ActionContractError(
                    f"Action {self.id!r} subagent.allowed_tools must be a list[str]"
                )
        if self.entry:
            entry_path = Path(self.entry)
            if entry_path.is_absolute():
                raise ActionContractError(f"Action {self.id!r} entry must be relative")
            if ".." in entry_path.parts:
                raise ActionContractError(f"Action {self.id!r} entry may not escape the package root")
            if package_root is not None and not (package_root / entry_path).exists():
                raise ActionContractError(
                    f"Action {self.id!r} entry does not exist inside package root: {self.entry!r}"
                )


@dataclass(frozen=True)
class ActionManifest:
    """Typed ``actions.yaml`` manifest."""

    schema_version: str
    actions: list[ActionSpec] = field(default_factory=list)
    default_action: Optional[str] = None
    source_path: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: Path | None = None) -> "ActionManifest":
        schema_version = str(data.get("schema_version", "")).strip()
        raw_actions = data.get("actions") or []
        default_action = data.get("default_action", data.get("default_action_id"))
        if default_action in {None, ""} and isinstance(raw_actions, list) and raw_actions:
            first = raw_actions[0]
            if isinstance(first, dict):
                default_action = first.get("id")
        metadata = {
            k: v
            for k, v in data.items()
            if k not in {"schema_version", "actions", "default_action", "default_action_id"}
        }

        if not isinstance(raw_actions, list):
            raise ActionContractError("actions must be a list")

        actions = [ActionSpec.from_dict(item) for item in raw_actions]
        manifest = cls(
            schema_version=schema_version,
            actions=actions,
            default_action=default_action,
            source_path=source_path,
            metadata=metadata,
        )
        manifest.validate()
        return manifest

    @classmethod
    def load(cls, source: str | Path | dict[str, Any]) -> "ActionManifest":
        source_path: Optional[Path] = None
        if isinstance(source, Path):
            source_path = source
        try:
            mapping = load_actions_mapping(source)
        except Exception as exc:  # skill_contract surfaces parse errors here
            raise ActionContractError(str(exc)) from exc
        return cls.from_dict(mapping, source_path=source_path)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "actions": [action.to_dict() for action in self.actions],
        }
        if self.default_action is not None:
            result["default_action"] = self.default_action
        if self.metadata:
            result.update(self.metadata)
        return result

    def validate(self, package_root: Path | None = None) -> None:
        if self.schema_version != "actions.v1":
            raise ActionContractError(
                f"Unsupported actions schema_version: {self.schema_version!r}"
            )
        if not self.actions:
            raise ActionContractError("actions manifest must declare at least one action")

        seen: set[str] = set()
        for action in self.actions:
            action.validate(package_root=package_root)
            if action.id in seen:
                raise ActionContractError(f"Duplicate action id: {action.id!r}")
            seen.add(action.id)

        if self.default_action is not None and self.default_action not in seen:
            raise ActionContractError(
                f"default_action {self.default_action!r} is not declared in actions"
            )

    def get(self, action_id: str) -> ActionSpec:
        for action in self.actions:
            if action.id == action_id:
                return action
        raise KeyError(action_id)

    def has(self, action_id: str) -> bool:
        try:
            self.get(action_id)
        except KeyError:
            return False
        return True

    def action_ids(self) -> list[str]:
        return [action.id for action in self.actions]


def parse_actions_yaml(raw: str | dict[str, Any] | Path) -> ActionManifest:
    """Parse an ``actions.yaml`` payload into a typed manifest."""

    return ActionManifest.load(raw)


def load_actions_manifest(path: str | Path) -> ActionManifest:
    """Load and parse ``actions.yaml`` from disk."""

    return ActionManifest.load(Path(path))
