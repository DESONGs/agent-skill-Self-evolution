from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ContractSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ContractIssue(BaseModel):
    code: str
    message: str
    severity: ContractSeverity = ContractSeverity.ERROR
    location: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ContractParseError(Exception):
    def __init__(self, issues: list[ContractIssue], source: str | None = None):
        self.issues = issues
        self.source = source
        message = "; ".join(issue.message for issue in issues) if issues else "Contract parse failed"
        if source:
            message = f"{source}: {message}"
        super().__init__(message)


class ContractValidationReport(BaseModel):
    ok: bool
    issues: list[ContractIssue] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_issues(cls, issues: list[ContractIssue]) -> "ContractValidationReport":
        return cls(ok=not any(issue.severity == ContractSeverity.ERROR for issue in issues), issues=issues)

    def merged(self, other: "ContractValidationReport") -> "ContractValidationReport":
        return self.__class__.from_issues([*self.issues, *other.issues])


def validation_error_to_issues(
    exc: ValidationError,
    source: str,
    severity: ContractSeverity = ContractSeverity.ERROR,
) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for error in exc.errors(include_url=False):
        location = ".".join(str(part) for part in error.get("loc", ())) or None
        issues.append(
            ContractIssue(
                code=error.get("type", "validation_error"),
                message=error.get("msg", "Validation failed"),
                severity=severity,
                location=location,
                details={
                    "source": source,
                    "input": error.get("input"),
                },
            )
        )
    return issues


def path_issue(
    code: str,
    message: str,
    *,
    path: Path | str | None = None,
    details: dict[str, Any] | None = None,
    severity: ContractSeverity = ContractSeverity.ERROR,
) -> ContractIssue:
    payload = dict(details or {})
    if path is not None:
        payload["path"] = str(path)
    return ContractIssue(code=code, message=message, severity=severity, location=str(path) if path else None, details=payload)


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
        return [part.strip().strip("'\"") for part in raw.split(",") if part.strip()]
    return [str(value).strip()]


class SkillFrontmatter(BaseModel):
    name: str
    description: str
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    owner: str | None = None
    status: Literal["experimental", "active", "deprecated"] | None = None
    allowed_tools: list[str] = Field(default_factory=list, alias="allowed-tools")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("tags", "allowed_tools", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_string_list(value)


class SkillMdDocument(BaseModel):
    path: Path
    frontmatter: SkillFrontmatter
    body: str

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class SkillManifest(BaseModel):
    name: str
    version: str
    owner: str
    updated_at: date
    status: Literal["experimental", "active", "deprecated"]
    maturity_tier: Literal["scaffold", "production", "library", "governed"]
    lifecycle_stage: str | None = None
    context_budget_tier: str | None = None
    review_cadence: Literal["monthly", "quarterly", "semiannual", "annual", "per-release"]
    target_platforms: list[str] = Field(default_factory=list)
    factory_components: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] | None = None
    default_runtime_profile: str | None = None
    deprecation_note: str | None = None

    model_config = ConfigDict(extra="allow")


class SkillAction(BaseModel):
    id: str
    kind: Literal["script", "mcp", "instruction", "subagent"]
    entry: str | None = None
    runtime: str | None = None
    timeout_sec: int
    sandbox: Literal["read-only", "workspace-write", "network-allowed"]
    allow_network: bool = False
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    side_effects: list[str] = Field(default_factory=list)
    idempotency: Literal["exact", "best_effort", "none"] | None = None
    default: bool = False

    model_config = ConfigDict(extra="allow")


class SkillActionsDocument(BaseModel):
    schema_version: str
    actions: list[SkillAction]
    default_action_id: str | None = Field(default=None, alias="default_action")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def _validate_defaults(self) -> "SkillActionsDocument":
        action_ids = [action.id for action in self.actions]
        if self.default_action_id is None:
            self.default_action_id = next(
                (action.id for action in self.actions if action.default),
                self.actions[0].id if self.actions else None,
            )
        if self.default_action_id is not None and self.default_action_id not in action_ids:
            raise ValueError(f"default_action must reference a declared action: {self.default_action_id}")
        return self


class SkillActivation(BaseModel):
    mode: Literal["manual", "path_scoped"]
    paths: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class SkillExecution(BaseModel):
    context: Literal["inline", "fork"]
    shell: Literal["bash", "powershell"]

    model_config = ConfigDict(extra="allow")


class SkillTrust(BaseModel):
    source_tier: Literal["local", "managed", "plugin", "remote"]
    remote_inline_execution: Literal["forbid", "allow"]
    remote_metadata_policy: str

    model_config = ConfigDict(extra="allow")


class SkillCompatibility(BaseModel):
    canonical_format: str
    adapter_targets: list[str]
    activation: SkillActivation
    execution: SkillExecution
    trust: SkillTrust
    degradation: dict[str, str]

    model_config = ConfigDict(extra="allow")


class SkillInterfaceDocument(BaseModel):
    interface: dict[str, str]
    compatibility: SkillCompatibility

    model_config = ConfigDict(extra="allow")


class ParsedSkillPackage(BaseModel):
    root: Path
    skill_md: SkillMdDocument
    manifest: SkillManifest
    actions: SkillActionsDocument
    interface: SkillInterfaceDocument

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
