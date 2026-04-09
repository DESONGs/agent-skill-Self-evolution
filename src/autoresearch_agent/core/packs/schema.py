from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PACK_MANIFEST_SCHEMA_VERSION = "pack.manifest.v1"
RESEARCH_SPEC_SCHEMA_VERSION = "research.yaml.v1"
DEFAULT_RESEARCH_RUNTIME = {
    "provider": "openai",
    "model": "gpt-5.4",
    "api_base_url": "",
    "env_refs": [],
    "secret_refs": [],
    "concurrency": 1,
}
DEFAULT_RESEARCH_CONSTRAINTS = {
    "total_token_budget": 0,
    "per_eval_token_budget": 150000,
    "max_completion_tokens": 1200,
    "eval_timeout_seconds": 900,
    "max_runtime_minutes": 0,
    "max_memory_mb": 4096,
    "max_cpu_seconds": 7200,
    "allow_network": False,
    "real_execution": False,
    "preserve_run": False,
    "retention_hours": 168,
}
DEFAULT_RESEARCH_EVALUATION = {
    "sample_size": 200,
    "search_repeats": 2,
    "validation_repeats": 2,
    "holdout_repeats": 1,
    "gate_profile": "balanced",
    "gate_overrides": {},
    "emit_breakdowns": True,
}
DEFAULT_RESEARCH_SEARCH = {
    "mode": "self_iterate",
    "editable_targets": ["workspace/strategy.py"],
    "allowed_axes": [],
    "frozen_axes": [],
    "max_iterations": 10,
    "candidates_per_iteration": 3,
    "mutation_policy": "single_target_patch",
    "allow_prompt_edits": True,
    "allow_feature_edits": True,
    "allow_risk_edits": True,
}
DEFAULT_RESEARCH_DATA = {
    "source": "",
    "format": "auto",
    "adapter": "auto",
    "snapshot_on_run": True,
    "schema_map": {},
    "filters": {},
    "sampling": {
        "mode": "fixed_count",
        "max_records": 200,
        "seed": 42,
    },
    "split": {
        "mode": "auto",
        "train_ratio": None,
        "validation_ratio": None,
        "holdout_ratio": None,
    },
}


def _copy_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {key: _copy_value(item) for key, item in value.items()}


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _copy_mapping(value)
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return value


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = _copy_mapping(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = _copy_value(value)
    return merged


def _ensure_list_of_str(name: str, value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be list[str]")
    return [item.strip() for item in value if item.strip()]


def _ensure_mapping(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be object")
    return value


@dataclass(frozen=True)
class PackManifest:
    schema_version: str
    pack_id: str
    name: str
    version: str
    description: str
    domain: str
    entry_profile: str
    supported_formats: list[str]
    default_adapter: str
    default_objective: str
    axes_catalog: dict[str, Any]
    editable_targets: list[str]
    entrypoints: dict[str, Any]
    defaults: dict[str, Any]
    security: dict[str, Any]
    compatibility: dict[str, Any]
    manifest_path: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed_axes(self) -> list[str]:
        return list(self.axes_catalog.keys())

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "domain": self.domain,
            "entry_profile": self.entry_profile,
            "supported_formats": list(self.supported_formats),
            "default_adapter": self.default_adapter,
            "default_objective": self.default_objective,
            "axes_catalog": _copy_mapping(self.axes_catalog),
            "editable_targets": list(self.editable_targets),
            "entrypoints": _copy_mapping(self.entrypoints),
            "defaults": _copy_mapping(self.defaults),
            "security": _copy_mapping(self.security),
            "compatibility": _copy_mapping(self.compatibility),
        }
        if self.manifest_path:
            payload["manifest_path"] = self.manifest_path
        if self.raw:
            payload["raw"] = _copy_mapping(self.raw)
        return payload


@dataclass(frozen=True)
class ResearchSpec:
    schema_version: str
    project: dict[str, Any]
    pack: dict[str, Any]
    data: dict[str, Any]
    objective: dict[str, Any]
    search: dict[str, Any]
    evaluation: dict[str, Any]
    constraints: dict[str, Any]
    runtime: dict[str, Any]
    outputs: dict[str, Any]
    pack_config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project": _copy_mapping(self.project),
            "pack": _copy_mapping(self.pack),
            "data": _copy_mapping(self.data),
            "objective": _copy_mapping(self.objective),
            "search": _copy_mapping(self.search),
            "evaluation": _copy_mapping(self.evaluation),
            "constraints": _copy_mapping(self.constraints),
            "runtime": _copy_mapping(self.runtime),
            "outputs": _copy_mapping(self.outputs),
            "pack_config": _copy_mapping(self.pack_config),
        }


def normalize_pack_manifest(payload: dict[str, Any], *, manifest_path: str = "") -> PackManifest:
    if not isinstance(payload, dict):
        raise ValueError("pack manifest must be an object")

    required_fields = [
        "schema_version",
        "pack_id",
        "name",
        "version",
        "description",
        "domain",
        "entry_profile",
        "supported_formats",
        "default_adapter",
        "default_objective",
        "axes_catalog",
        "editable_targets",
        "entrypoints",
        "defaults",
        "security",
        "compatibility",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"pack manifest missing required fields: {', '.join(missing)}")

    schema_version = str(payload["schema_version"])
    if schema_version != PACK_MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"unsupported pack manifest schema: {schema_version}")

    supported_formats = _ensure_list_of_str("supported_formats", payload["supported_formats"])
    editable_targets = _ensure_list_of_str("editable_targets", payload["editable_targets"])
    axes_catalog = _ensure_mapping("axes_catalog", payload["axes_catalog"])
    entrypoints = _ensure_mapping("entrypoints", payload["entrypoints"])
    defaults = _ensure_mapping("defaults", payload["defaults"])
    security = _ensure_mapping("security", payload["security"])
    compatibility = _ensure_mapping("compatibility", payload["compatibility"])

    normalized_axes: dict[str, Any] = {}
    for axis_name, axis_payload in axes_catalog.items():
        if not isinstance(axis_name, str) or not axis_name.strip():
            raise ValueError("axes_catalog keys must be non-empty strings")
        if not isinstance(axis_payload, dict):
            raise ValueError(f"axes_catalog.{axis_name} must be object")
        normalized_axes[axis_name] = _copy_mapping(axis_payload)

    return PackManifest(
        schema_version=schema_version,
        pack_id=str(payload["pack_id"]).strip(),
        name=str(payload["name"]).strip(),
        version=str(payload["version"]).strip(),
        description=str(payload["description"]).strip(),
        domain=str(payload["domain"]).strip(),
        entry_profile=str(payload["entry_profile"]).strip(),
        supported_formats=supported_formats,
        default_adapter=str(payload["default_adapter"]).strip(),
        default_objective=str(payload["default_objective"]).strip(),
        axes_catalog=normalized_axes,
        editable_targets=editable_targets,
        entrypoints=_copy_mapping(entrypoints),
        defaults=_copy_mapping(defaults),
        security=_copy_mapping(security),
        compatibility=_copy_mapping(compatibility),
        manifest_path=manifest_path,
        raw=_copy_mapping(payload),
    )


def build_default_research_spec(
    *,
    project_name: str,
    pack_id: str,
    data_source: str,
    editable_target: str = "workspace/strategy.py",
    allowed_axes: list[str] | None = None,
    pack_config: dict[str, Any] | None = None,
) -> ResearchSpec:
    search = merge_dict(
        DEFAULT_RESEARCH_SEARCH,
        {
            "editable_targets": [editable_target],
            "allowed_axes": list(allowed_axes or []),
        },
    )
    data = merge_dict(DEFAULT_RESEARCH_DATA, {"source": data_source})
    runtime = merge_dict(DEFAULT_RESEARCH_RUNTIME, {})
    pack_payload = {"id": pack_id, "version": "latest", "entry_profile": "default"}
    pack_config_payload = _copy_mapping(pack_config or {})
    return ResearchSpec(
        schema_version=RESEARCH_SPEC_SCHEMA_VERSION,
        project={
            "name": project_name,
            "description": "",
            "workspace_dir": "./workspace",
            "artifacts_dir": "./artifacts",
            "runs_dir": "./.autoresearch/runs",
        },
        pack=pack_payload,
        data=data,
        objective={
            "primary": "maximize_pnl",
            "secondary": ["maximize_accuracy", "minimize_drawdown"],
            "direction": "maximize",
            "stop_when": {"metric": "", "threshold": None},
            "notes": "",
        },
        search=search,
        evaluation=_copy_mapping(DEFAULT_RESEARCH_EVALUATION),
        constraints=_copy_mapping(DEFAULT_RESEARCH_CONSTRAINTS),
        runtime=runtime,
        outputs={
            "write_patch": True,
            "write_report": True,
            "write_dataset_profile": True,
            "write_best_strategy": True,
            "export_format": "json",
        },
        pack_config=pack_config_payload,
    )
