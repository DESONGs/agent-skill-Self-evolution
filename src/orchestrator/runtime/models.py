"""Data models for skill orchestration - simplified."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass as std_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from constants import TaskStatus as NodeStatus  # noqa: F401 — re-exported
from skill_contract.models import ContractParseError, ContractSeverity
from skill_contract.parsers.actions import parse_actions as parse_contract_actions
from skill_contract.parsers.interface import parse_interface as parse_contract_interface
from skill_contract.parsers.manifest import parse_manifest as parse_contract_manifest
from skill_contract.parsers.package import load_skill_package as load_contract_package
from skill_contract.parsers.skill_md import parse_skill_md as parse_contract_skill_md
from skill_contract.validators.actions import validate_actions as validate_contract_actions
from skill_contract.validators.interface import validate_interface as validate_contract_interface
from skill_contract.validators.manifest import validate_manifest as validate_contract_manifest
from skill_contract.validators.package import validate_skill_package as validate_source_skill_package
from skill_contract.validators.skill_md import validate_skill_md as validate_contract_skill_md


VALID_ACTION_KINDS = {"script", "mcp", "instruction", "subagent"}
VALID_EXECUTION_CONTEXTS = {"inline", "fork"}
VALID_SANDBOXES = {"read-only", "workspace-write", "network-allowed"}
VALID_SOURCE_TIERS = {"local", "managed", "plugin", "remote"}


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        return [part.strip().strip("'\"") for part in re.split(r"[,\n]", raw) if part.strip()]
    return [str(value).strip()]


def parse_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and return the body content."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, content

    frontmatter_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])

    try:
        payload = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        return {}, body

    if not isinstance(payload, dict):
        return {}, body
    return payload, body


def read_json_payload(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def read_yaml_payload(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return None, None
    except yaml.YAMLError as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "YAML document must be a mapping"
    return payload, None


def _safe_model_validate(
    model: type[BaseModel],
    payload: dict[str, Any] | None,
    errors: list[str],
    label: str,
) -> BaseModel | None:
    if payload is None:
        return None
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        errors.append(f"{label} validation failed: {exc.errors(include_url=False)}")
        return None


def _path_within_root(root: Path, candidate: str) -> bool:
    if not candidate:
        return False
    entry_path = Path(candidate)
    if entry_path.is_absolute():
        return False
    resolved = (root / entry_path).resolve()
    return resolved == root.resolve() or root.resolve() in resolved.parents


def _skill_frontmatter_from_source(skill_md_document) -> "SkillFrontmatter":
    payload = skill_md_document.frontmatter.model_dump(mode="json")
    payload["version"] = payload.get("version") or ""
    payload["tags"] = payload.get("tags") or []
    payload["category"] = payload.get("category") or "other"
    payload["owner"] = payload.get("owner") or ""
    payload["status"] = payload.get("status") or ""
    payload["metadata"] = payload.get("metadata") or {}
    return SkillFrontmatter.model_validate(payload)


def _skill_manifest_from_source(manifest_document) -> "SkillManifest":
    payload = manifest_document.model_dump(mode="json")
    payload["updated_at"] = str(payload.get("updated_at", ""))
    payload["lifecycle_stage"] = payload.get("lifecycle_stage") or ""
    payload["context_budget_tier"] = payload.get("context_budget_tier") or "production"
    payload["target_platforms"] = payload.get("target_platforms") or []
    payload["factory_components"] = payload.get("factory_components") or []
    payload["risk_level"] = payload.get("risk_level") or "medium"
    payload["default_runtime_profile"] = payload.get("default_runtime_profile") or ""
    payload["deprecation_note"] = payload.get("deprecation_note")
    return SkillManifest.model_validate(payload)


def _skill_actions_from_source(actions_document) -> "SkillActionsContract":
    payload = actions_document.model_dump(mode="json")
    normalized_actions: list[dict[str, Any]] = []
    for action in payload.get("actions", []):
        normalized = dict(action)
        normalized["entry"] = normalized.get("entry") or ""
        normalized["runtime"] = normalized.get("runtime") or ""
        normalized["timeout_sec"] = normalized.get("timeout_sec") or (
            1 if normalized.get("kind") == "instruction" else 0
        )
        normalized["sandbox"] = normalized.get("sandbox") or "read-only"
        normalized["input_schema"] = normalized.get("input_schema") or {}
        normalized["output_schema"] = normalized.get("output_schema") or {}
        normalized["side_effects"] = normalized.get("side_effects") or []
        normalized["idempotency"] = normalized.get("idempotency") or "best_effort"
        normalized["default"] = bool(normalized.get("default", False))
        normalized_actions.append(normalized)

    default_action_id = payload.get("default_action")
    if not default_action_id:
        default_action_id = next(
            (action.get("id") for action in normalized_actions if action.get("default")),
            normalized_actions[0].get("id") if normalized_actions else None,
        )
    return SkillActionsContract.model_validate(
        {
            "schema_version": payload.get("schema_version", "actions.v1"),
            "actions": normalized_actions,
            "default_action_id": default_action_id,
        }
    )


def _skill_interface_from_source(interface_document) -> "SkillInterface":
    payload = interface_document.model_dump(mode="json")
    return SkillInterface.model_validate(payload)


def _contract_files(skill_root: Path) -> list[str]:
    return [
        rel
        for rel in (
            "SKILL.md",
            "manifest.json",
            "actions.yaml",
            "agents/interface.yaml",
        )
        if (skill_root / rel).exists()
    ]


class SkillFrontmatter(BaseModel):
    """Parsed SKILL.md frontmatter."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    description: str
    version: str = ""
    tags: list[str] = Field(default_factory=list)
    category: str = "other"
    owner: str = ""
    status: str = ""
    allowed_tools: list[str] = Field(default_factory=list, alias="allowed-tools")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", "allowed_tools", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)


class SkillManifest(BaseModel):
    """Parsed manifest.json governance metadata."""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str
    owner: str
    updated_at: str
    status: str
    maturity_tier: str
    lifecycle_stage: str
    context_budget_tier: str = "production"
    review_cadence: str
    target_platforms: list[str] = Field(default_factory=list)
    factory_components: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    default_runtime_profile: str = ""
    deprecation_note: str | None = None

    @field_validator("target_platforms", "factory_components", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)

    @field_validator("updated_at")
    @classmethod
    def _validate_updated_at(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value


class SkillAction(BaseModel):
    """Single action contract entry from actions.yaml."""

    model_config = ConfigDict(extra="allow")

    id: str
    kind: str
    entry: str = ""
    runtime: str = ""
    timeout_sec: int = 0
    sandbox: str = "read-only"
    allow_network: bool = False
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    side_effects: list[str] = Field(default_factory=list)
    idempotency: str | None = None
    default: bool = False
    description: str = ""
    telemetry: dict[str, Any] = Field(default_factory=dict)
    mcp: dict[str, Any] = Field(default_factory=dict)
    subagent: dict[str, Any] = Field(default_factory=dict)

    @field_validator("side_effects", mode="before")
    @classmethod
    def _coerce_side_effects(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)

    @model_validator(mode="after")
    def _validate_contract(self) -> "SkillAction":
        if self.kind not in VALID_ACTION_KINDS:
            raise ValueError(f"Unsupported action kind: {self.kind}")
        if self.sandbox not in VALID_SANDBOXES:
            raise ValueError(f"Unsupported sandbox: {self.sandbox}")
        if self.kind == "instruction":
            if self.timeout_sec < 0:
                raise ValueError("timeout_sec must be non-negative")
            return self
        if self.kind == "script":
            if self.timeout_sec <= 0:
                raise ValueError("timeout_sec must be a positive integer")
            if not self.entry.strip():
                raise ValueError("entry is required")
            if not self.runtime.strip():
                raise ValueError("script actions require runtime")
            return self
        if self.timeout_sec < 0:
            raise ValueError("timeout_sec must be non-negative")
        return self


class SkillActionsContract(BaseModel):
    """Parsed actions.yaml contract."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "actions.v1"
    actions: list[SkillAction] = Field(default_factory=list)
    default_action_id: str | None = None

    @model_validator(mode="after")
    def _validate_contract(self) -> "SkillActionsContract":
        if self.schema_version != "actions.v1":
            raise ValueError("schema_version must be actions.v1")
        if not self.actions:
            raise ValueError("actions.yaml must declare at least one action")
        action_ids = [action.id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("action ids must be unique")
        if self.default_action_id is None:
            self.default_action_id = next(
                (action.id for action in self.actions if action.default),
                self.actions[0].id,
            )
        if self.default_action_id not in action_ids:
            raise ValueError(f"default_action_id must reference a declared action: {self.default_action_id}")
        return self

    def get_action(self, action_id: str) -> SkillAction:
        for action in self.actions:
            if action.id == action_id:
                return action
        raise KeyError(action_id)

    def has_action(self, action_id: str) -> bool:
        try:
            self.get_action(action_id)
        except KeyError:
            return False
        return True

    def resolved_default_action_id(self) -> str | None:
        if self.default_action_id and self.has_action(self.default_action_id):
            return self.default_action_id
        return self.actions[0].id if self.actions else None

    def declared_action_ids(self) -> list[str]:
        return [action.id for action in self.actions]

    def declared_actions(self) -> list[SkillAction]:
        return list(self.actions)


class SkillInterfaceInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    display_name: str
    short_description: str
    default_prompt: str


class SkillActivation(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: str
    paths: list[str] = Field(default_factory=list)

    @field_validator("paths", mode="before")
    @classmethod
    def _coerce_paths(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)


class SkillExecution(BaseModel):
    model_config = ConfigDict(extra="allow")

    context: str
    shell: str

    @model_validator(mode="after")
    def _validate_contract(self) -> "SkillExecution":
        if self.context not in VALID_EXECUTION_CONTEXTS:
            raise ValueError(f"Unsupported execution context: {self.context}")
        return self


class SkillTrust(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_tier: str
    remote_inline_execution: str
    remote_metadata_policy: str

    @model_validator(mode="after")
    def _validate_contract(self) -> "SkillTrust":
        if self.source_tier not in VALID_SOURCE_TIERS:
            raise ValueError(f"Unsupported source tier: {self.source_tier}")
        if self.remote_inline_execution not in {"forbid", "allow"}:
            raise ValueError("remote_inline_execution must be forbid or allow")
        if not self.remote_metadata_policy:
            raise ValueError("remote_metadata_policy is required")
        return self


class SkillCompatibility(BaseModel):
    model_config = ConfigDict(extra="allow")

    canonical_format: str
    adapter_targets: list[str] = Field(default_factory=list)
    activation: SkillActivation
    execution: SkillExecution
    trust: SkillTrust
    degradation: dict[str, str] = Field(default_factory=dict)

    @field_validator("adapter_targets", mode="before")
    @classmethod
    def _coerce_adapter_targets(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)

    @field_validator("degradation", mode="before")
    @classmethod
    def _coerce_degradation(cls, value: Any) -> dict[str, str]:
        return value if isinstance(value, dict) else {}

    @model_validator(mode="after")
    def _validate_contract(self) -> "SkillCompatibility":
        if not self.canonical_format:
            raise ValueError("canonical_format is required")
        missing = [target for target in self.adapter_targets if target not in self.degradation]
        if missing:
            raise ValueError(f"degradation missing entries for targets: {missing}")
        return self


class SkillInterface(BaseModel):
    model_config = ConfigDict(extra="allow")

    interface: SkillInterfaceInfo
    compatibility: SkillCompatibility


class SkillPackageContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    package_root: str
    frontmatter: SkillFrontmatter
    manifest: SkillManifest | None = None
    actions: SkillActionsContract | None = None
    interface: SkillInterface | None = None
    body: str = ""
    contract_files: list[str] = Field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.frontmatter.name

    @property
    def action_ids(self) -> list[str]:
        if not self.actions:
            return []
        return self.actions.declared_action_ids()

    @property
    def default_action_id(self) -> str | None:
        return self.actions.resolved_default_action_id() if self.actions else None


class SkillPackageValidationReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    contract: SkillPackageContract | None = None


def _issue_message(issue: Any) -> str:
    location = getattr(issue, "location", None)
    if location:
        return f"{issue.message} ({location})"
    return issue.message


def _merge_source_report(report: Any, errors: list[str], warnings: list[str]) -> None:
    for issue in report.issues:
        if issue.severity == ContractSeverity.ERROR:
            errors.append(_issue_message(issue))
        else:
            warnings.append(_issue_message(issue))


def _build_runtime_contract(
    skill_root: Path,
    skill_md_document: Any,
    manifest_document: Any | None,
    actions_document: Any | None,
    interface_document: Any | None,
    *,
    body_limit: int,
) -> SkillPackageContract:
    return SkillPackageContract(
        package_root=str(skill_root),
        frontmatter=_skill_frontmatter_from_source(skill_md_document),
        manifest=_skill_manifest_from_source(manifest_document) if manifest_document is not None else None,
        actions=_skill_actions_from_source(actions_document) if actions_document is not None else None,
        interface=_skill_interface_from_source(interface_document) if interface_document is not None else None,
        body=skill_md_document.body[:body_limit],
        contract_files=_contract_files(skill_root),
    )


def validate_skill_package_contract(skill_path: Path, *, strict: bool = True) -> SkillPackageValidationReport:
    """Validate the package contract for a skill directory."""
    errors: list[str] = []
    warnings: list[str] = []
    skill_root = skill_path.resolve()
    skill_md_path = skill_root / "SKILL.md"
    if not skill_md_path.exists():
        errors.append("Missing SKILL.md")
        return SkillPackageValidationReport(ok=False, errors=errors, warnings=warnings)

    try:
        skill_md_document = parse_contract_skill_md(skill_md_path)
    except ContractParseError as exc:
        return SkillPackageValidationReport(
            ok=False,
            errors=[_issue_message(issue) for issue in exc.issues],
            warnings=warnings,
        )

    manifest_document = None
    manifest_path = skill_root / "manifest.json"
    if manifest_path.exists():
        try:
            manifest_document = parse_contract_manifest(manifest_path)
        except ContractParseError as exc:
            errors.extend(_issue_message(issue) for issue in exc.issues)
    elif strict:
        errors.append("Missing manifest.json")
    else:
        warnings.append("manifest.json is missing")

    actions_document = None
    actions_path = skill_root / "actions.yaml"
    if actions_path.exists():
        try:
            actions_document = parse_contract_actions(actions_path)
        except ContractParseError as exc:
            errors.extend(_issue_message(issue) for issue in exc.issues)
    elif strict:
        errors.append("Missing actions.yaml")
    else:
        warnings.append("legacy_actions_contract_missing: actions.yaml is missing; package is metadata-only")

    interface_document = None
    interface_path = skill_root / "agents" / "interface.yaml"
    if interface_path.exists():
        try:
            interface_document = parse_contract_interface(interface_path)
        except ContractParseError as exc:
            errors.extend(_issue_message(issue) for issue in exc.issues)
    elif strict:
        errors.append("Missing agents/interface.yaml")
    else:
        warnings.append("agents/interface.yaml is missing")

    if strict and not errors and manifest_document and actions_document and interface_document:
        package = load_contract_package(skill_root)
        _merge_source_report(validate_source_skill_package(skill_root), errors, warnings)
        contract = _build_runtime_contract(
            skill_root,
            package.skill_md,
            package.manifest,
            package.actions,
            package.interface,
            body_limit=5000,
        )
    else:
        partial_reports = [validate_contract_skill_md(skill_md_document, skill_root)]
        if manifest_document is not None:
            partial_reports.append(validate_contract_manifest(manifest_document, skill_md_document, manifest_path))
        if actions_document is not None:
            partial_reports.append(validate_contract_actions(actions_document))
        if interface_document is not None:
            partial_reports.append(validate_contract_interface(interface_document))
        for partial_report in partial_reports:
            _merge_source_report(partial_report, errors, warnings)
        contract = _build_runtime_contract(
            skill_root,
            skill_md_document,
            manifest_document,
            actions_document,
            interface_document,
            body_limit=5000,
        )

    return SkillPackageValidationReport(ok=not errors, errors=errors, warnings=warnings, contract=contract)


def load_skill_package_metadata(skill_path: Path, max_content_chars: int = 5000) -> "SkillMetadata":
    """Load skill metadata from SKILL.md plus optional contract files."""
    skill_root = skill_path.resolve()
    report = validate_skill_package_contract(skill_root, strict=False)
    contract = report.contract
    if contract is None:
        raise FileNotFoundError(f"Skill package missing or invalid SKILL.md: {skill_root}")

    frontmatter = contract.frontmatter
    manifest = contract.manifest
    interface = contract.interface
    actions = contract.actions

    display_name = interface.interface.display_name if interface else frontmatter.name
    short_description = interface.interface.short_description if interface else frontmatter.description
    default_prompt = interface.interface.default_prompt if interface else frontmatter.description
    action_ids = contract.action_ids
    default_action_id = contract.default_action_id

    return SkillMetadata(
        name=frontmatter.name,
        description=frontmatter.description,
        path=str(skill_root),
        package_root=str(skill_root),
        slug=frontmatter.name,
        version=frontmatter.version or (manifest.version if manifest else ""),
        allowed_tools=frontmatter.allowed_tools,
        category=frontmatter.category or "other",
        content=contract.body[:max_content_chars],
        display_name=display_name,
        short_description=short_description,
        default_prompt=default_prompt,
        action_ids=action_ids,
        default_action_id=default_action_id,
        manifest=manifest,
        actions_contract=actions,
        interface_contract=interface,
        contract=contract,
        contract_files=contract.contract_files,
        contract_errors=report.errors,
        contract_warnings=report.warnings,
        has_actions_contract=actions is not None,
        uses_legacy_allowed_tools=bool(frontmatter.allowed_tools),
    )


# =============================================================================
# SDK Metrics (standard dataclass, not Pydantic)
# =============================================================================


@std_dataclass
class SDKMetrics:
    """Metrics from a single Claude Agent SDK ResultMessage."""

    duration_ms: int = 0
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    num_turns: int = 0
    is_error: bool = False
    subtype: str = ""

    @classmethod
    def from_result_message(cls, message) -> "SDKMetrics":
        """Extract metrics from a Claude Agent SDK ResultMessage."""
        return cls(
            duration_ms=getattr(message, "duration_ms", 0) or 0,
            total_cost_usd=getattr(message, "total_cost_usd", 0.0) or 0.0,
            input_tokens=getattr(message, "input_tokens", 0) or 0,
            output_tokens=getattr(message, "output_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(message, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(message, "cache_read_input_tokens", 0) or 0,
            num_turns=getattr(message, "num_turns", 0) or 0,
            is_error=getattr(message, "is_error", False) or False,
            subtype=getattr(message, "subtype", "") or "",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "duration_ms": self.duration_ms,
            "total_cost_usd": self.total_cost_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "num_turns": self.num_turns,
            "is_error": self.is_error,
            "subtype": self.subtype,
        }

    @staticmethod
    def aggregate(
        phase_node_metrics: list[list[tuple[str, "SDKMetrics"]]],
        extra_metrics: dict[str, "SDKMetrics"] | None = None,
    ) -> dict:
        """Phase-aware aggregation.

        - extra_metrics (e.g. planning): duration added directly
        - phase_node_metrics: per-phase max duration, cross-phase sum
        - tokens/cost/num_turns: summed across all sessions
        - is_error: True if any session errored
        - Multi-node: includes node_metrics sub-dict
        """
        all_metrics: list[SDKMetrics] = []
        node_metrics_map: dict[str, dict] = {}
        session_count = 0

        # Extra metrics (planning, etc.) — duration adds directly
        extra_duration = 0
        if extra_metrics:
            for name, m in extra_metrics.items():
                all_metrics.append(m)
                node_metrics_map[name] = m.to_dict()
                extra_duration += m.duration_ms
                session_count += 1

        # Phase-aware duration: per-phase max, then sum across phases
        phase_duration = 0
        for phase_list in phase_node_metrics:
            if not phase_list:
                continue
            phase_max = 0
            for node_name, m in phase_list:
                all_metrics.append(m)
                node_metrics_map[node_name] = m.to_dict()
                session_count += 1
                if m.duration_ms > phase_max:
                    phase_max = m.duration_ms
            phase_duration += phase_max

        total_duration = extra_duration + phase_duration

        # Sum all additive fields
        result: dict = {
            "duration_ms": total_duration,
            "total_cost_usd": sum(m.total_cost_usd for m in all_metrics),
            "input_tokens": sum(m.input_tokens for m in all_metrics),
            "output_tokens": sum(m.output_tokens for m in all_metrics),
            "cache_creation_input_tokens": sum(m.cache_creation_input_tokens for m in all_metrics),
            "cache_read_input_tokens": sum(m.cache_read_input_tokens for m in all_metrics),
            "num_turns": sum(m.num_turns for m in all_metrics),
            "is_error": any(m.is_error for m in all_metrics),
            "session_count": session_count,
        }

        # Only include node_metrics when there are multiple nodes
        if len(node_metrics_map) > 1:
            result["node_metrics"] = node_metrics_map

        return result


# =============================================================================
# Enums
# =============================================================================


class SkillType(str, Enum):
    """Type of skill in the orchestration graph."""

    PRIMARY = "primary"  # Produces final deliverables
    HELPER = "helper"  # Supports primary or other helpers


class NodeFailureReason(str, Enum):
    """Reason for node execution failure."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SKILL_ERROR = "skill_error"

    UNKNOWN = "unknown"
    EXECUTION_ERROR = "execution_error"


# =============================================================================
# Pydantic Models
# =============================================================================


class SkillMetadata(BaseModel):
    """Metadata parsed from a skill package contract."""

    model_config = ConfigDict(frozen=True, extra="allow")

    name: str
    description: str
    path: str
    package_root: str = ""
    slug: str = ""
    version: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    category: str = "other"
    content: str = ""
    display_name: str = ""
    short_description: str = ""
    default_prompt: str = ""
    action_ids: list[str] = Field(default_factory=list)
    default_action_id: Optional[str] = None
    manifest: Optional[SkillManifest] = None
    actions_contract: Optional[SkillActionsContract] = None
    interface_contract: Optional[SkillInterface] = None
    contract: Optional[SkillPackageContract] = None
    contract_files: list[str] = Field(default_factory=list)
    contract_errors: list[str] = Field(default_factory=list)
    contract_warnings: list[str] = Field(default_factory=list)
    has_actions_contract: bool = False
    uses_legacy_allowed_tools: bool = False

    def supports_action(self, action_id: str) -> bool:
        return action_id in self.declared_action_ids()

    def declared_actions(self) -> list[SkillAction]:
        if self.actions_contract is not None:
            return self.actions_contract.declared_actions()
        return []

    def declared_action_ids(self) -> list[str]:
        if self.actions_contract is not None:
            return self.actions_contract.declared_action_ids()
        return list(self.action_ids)

    def get_declared_action(self, action_id: str) -> SkillAction | None:
        if self.actions_contract is None:
            return None
        try:
            return self.actions_contract.get_action(action_id)
        except KeyError:
            return None

    def resolved_default_action_id(self) -> Optional[str]:
        if self.default_action_id and self.supports_action(self.default_action_id):
            return self.default_action_id
        if self.action_ids:
            return self.action_ids[0]
        declared = self.declared_action_ids()
        return declared[0] if declared else None


class SkillNode(BaseModel):
    """Represents a skill in the dependency graph."""

    id: str
    name: str
    skill_type: SkillType = SkillType.HELPER
    depends_on: list[str] = Field(default_factory=list)
    purpose: str = ""
    status: NodeStatus = NodeStatus.PENDING
    output_path: Optional[str] = None
    action_id: Optional[str] = None
    action_input: dict[str, Any] = Field(default_factory=dict)
    # Collaboration fields
    outputs_summary: str = ""  # Expected outputs description
    downstream_hint: str = ""  # Role in workflow + quality requirements
    usage_hints: dict[str, str] = Field(default_factory=dict)  # {consumer_node_id: usage_instruction}

    @property
    def is_terminal(self) -> bool:
        """Check if node is in a terminal state."""
        return self.status in {
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.skill_type.value,
            "depends_on": self.depends_on,
            "purpose": self.purpose,
            "status": self.status.value,
        }
        if self.output_path:
            result["output_path"] = self.output_path
        if self.action_id is not None:
            result["action_id"] = self.action_id
        if self.action_input:
            result["action_input"] = self.action_input
        return result


class ExecutionPhase(BaseModel):
    """A group of skills that can run in parallel."""

    phase_number: int
    nodes: list[str]
    mode: str = "parallel"  # parallel | sequential

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "phase": self.phase_number,
            "mode": self.mode,
            "nodes": self.nodes,
        }


class NodeExecutionResult(BaseModel):
    """Result returned from an isolated session execution."""

    node_id: str
    status: NodeStatus
    output_path: Optional[str] = None
    summary: str = ""  # Brief summary of what was accomplished
    error: Optional[str] = None
    failure_reason: NodeFailureReason = NodeFailureReason.SUCCESS
    execution_time_seconds: float = 0.0
    cost_usd: float = 0.0
    sdk_metrics: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "node_id": self.node_id,
            "status": self.status.value,
            "failure_reason": self.failure_reason.value,
            "execution_time_seconds": self.execution_time_seconds,
        }
        if self.output_path:
            result["output_path"] = self.output_path
        if self.summary:
            result["summary"] = self.summary
        if self.error:
            result["error"] = self.error
        if self.cost_usd > 0:
            result["cost_usd"] = self.cost_usd
        if self.sdk_metrics:
            result["sdk_metrics"] = self.sdk_metrics
        return result
