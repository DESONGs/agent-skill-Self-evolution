from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any, Mapping


class ResearchSpecError(ValueError):
    """Raised when `research.yaml` is malformed or violates the contract."""


DEFAULT_RESEARCH_SPEC: dict[str, Any] = {
    "schema_version": "research.yaml.v1",
    "project": {
        "name": "my-research-project",
        "description": "",
        "workspace_dir": "workspace",
        "artifacts_dir": "artifacts",
        "runs_dir": ".autoresearch/runs",
    },
    "pack": {
        "id": "prediction_market",
        "version": "latest",
        "entry_profile": "default",
    },
    "data": {
        "source": "./datasets/input.json",
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
            "train_ratio": 0.7,
            "validation_ratio": 0.2,
            "holdout_ratio": 0.1,
        },
    },
    "objective": {
        "primary": "maximize_pnl",
        "secondary": ["maximize_accuracy", "minimize_drawdown"],
        "direction": "maximize",
        "stop_when": {
            "metric": "",
            "threshold": None,
        },
        "notes": "",
    },
    "search": {
        "mode": "self_iterate",
        "editable_targets": ["workspace/strategy.py"],
        "allowed_axes": [
            "prompt_factors",
            "confidence_threshold",
            "bet_sizing",
            "max_bet_fraction",
        ],
        "frozen_axes": [],
        "max_iterations": 10,
        "candidates_per_iteration": 3,
        "mutation_policy": "single_target_patch",
        "allow_prompt_edits": True,
        "allow_feature_edits": True,
        "allow_risk_edits": True,
    },
    "evaluation": {
        "sample_size": 200,
        "search_repeats": 2,
        "validation_repeats": 2,
        "holdout_repeats": 1,
        "gate_profile": "balanced",
        "gate_overrides": {},
        "emit_breakdowns": True,
    },
    "constraints": {
        "total_token_budget": 0,
        "per_eval_token_budget": 150_000,
        "max_completion_tokens": 1_200,
        "eval_timeout_seconds": 900,
        "max_runtime_minutes": 240,
        "max_memory_mb": 4096,
        "max_cpu_seconds": 7200,
        "allow_network": False,
        "real_execution": False,
        "preserve_run": False,
        "retention_hours": 168,
    },
    "runtime": {
        "provider": "openai",
        "model": "gpt-5.4",
        "api_base_url": "",
        "env_refs": [],
        "secret_refs": [],
        "concurrency": 1,
    },
    "outputs": {
        "write_patch": True,
        "write_report": True,
        "write_dataset_profile": True,
        "write_best_strategy": True,
        "export_format": "json",
    },
    "pack_config": {},
}


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def default_research_spec(
    *,
    project_name: str = "my-research-project",
    pack_id: str = "prediction_market",
    data_source: str = "./datasets/input.json",
    editable_target: str = "workspace/strategy.py",
) -> dict[str, Any]:
    spec = copy.deepcopy(DEFAULT_RESEARCH_SPEC)
    spec["project"]["name"] = project_name
    spec["pack"]["id"] = pack_id
    spec["data"]["source"] = data_source
    spec["search"]["editable_targets"] = [editable_target]
    return spec


def _parse_scalar(text: str) -> Any:
    value = text.strip()
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none", "~"}:
        return None
    if value.startswith(("{", "[", "\"", "'", "(")) or value.endswith(("}", "]", ")")):
        try:
            return json.loads(value)
        except Exception:
            try:
                return ast.literal_eval(value)
            except Exception:
                return value
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _tokenize_yaml(text: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append((indent, raw[indent:].rstrip()))
    return tokens


def _parse_block(tokens: list[tuple[int, str]], start: int, indent: int) -> tuple[Any, int]:
    if start >= len(tokens):
        return {}, start

    current_indent, current_line = tokens[start]
    if current_indent < indent:
        return {}, start

    if current_line.startswith("-"):
        items: list[Any] = []
        index = start
        while index < len(tokens):
            line_indent, line = tokens[index]
            if line_indent < indent:
                break
            if line_indent != indent or not line.startswith("-"):
                break
            item_text = line[1:].strip()
            index += 1
            if item_text:
                items.append(_parse_scalar(item_text))
                continue
            if index < len(tokens) and tokens[index][0] > indent:
                nested, index = _parse_block(tokens, index, tokens[index][0])
                items.append(nested)
            else:
                items.append(None)
        return items, index

    mapping: dict[str, Any] = {}
    index = start
    while index < len(tokens):
        line_indent, line = tokens[index]
        if line_indent < indent:
            break
        if line_indent != indent or line.startswith("-"):
            break
        if ":" not in line:
            raise ResearchSpecError(f"invalid YAML line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        index += 1
        if raw_value:
            mapping[key] = _parse_scalar(raw_value)
            continue
        if index < len(tokens) and tokens[index][0] > indent:
            nested, index = _parse_block(tokens, index, tokens[index][0])
            mapping[key] = nested
        else:
            mapping[key] = {}
    return mapping, index


def load_yaml_text(text: str) -> dict[str, Any]:
    tokens = _tokenize_yaml(text)
    if not tokens:
        return {}
    parsed, next_index = _parse_block(tokens, 0, tokens[0][0])
    if next_index != len(tokens):
        raise ResearchSpecError("failed to parse complete YAML document")
    if not isinstance(parsed, dict):
        raise ResearchSpecError("research.yaml must define a mapping at the top level")
    return parsed


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return repr(value)
    if isinstance(value, str):
        if value == "":
            return '""'
        safe = all(
            ch.isalnum() or ch in {"-", "_", ".", "/", ":", "@", "+", "="}
            for ch in value
        ) and not value[0].isspace() and not value[-1].isspace()
        return value if safe else json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def dump_research_yaml(spec: Mapping[str, Any]) -> str:
    normalized = validate_research_spec(dict(spec))

    def emit(value: Any, indent: int) -> list[str]:
        prefix = " " * indent
        if isinstance(value, dict):
            lines: list[str] = []
            if not value:
                return [f"{prefix}{{}}"]
            for key, item in value.items():
                if isinstance(item, dict):
                    if item:
                        lines.append(f"{prefix}{key}:")
                        lines.extend(emit(item, indent + 2))
                    else:
                        lines.append(f"{prefix}{key}: {{}}")
                elif isinstance(item, list):
                    if item:
                        lines.append(f"{prefix}{key}:")
                        lines.extend(emit(item, indent + 2))
                    else:
                        lines.append(f"{prefix}{key}: []")
                else:
                    lines.append(f"{prefix}{key}: {_format_scalar(item)}")
            return lines
        if isinstance(value, list):
            lines = []
            if not value:
                return [f"{prefix}[]"]
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}-")
                    lines.extend(emit(item, indent + 2))
                elif isinstance(item, list):
                    lines.append(f"{prefix}-")
                    lines.extend(emit(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {_format_scalar(item)}")
            return lines
        return [f"{prefix}{_format_scalar(value)}"]

    return "\n".join(emit(normalized, 0)).rstrip() + "\n"


def normalize_research_spec(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    normalized = _deep_merge(DEFAULT_RESEARCH_SPEC, payload)
    if "dataset" in payload and isinstance(payload["dataset"], Mapping):
        normalized["data"] = _deep_merge(normalized["data"], payload["dataset"])  # compatibility alias
    normalized["project"] = _coerce_mapping(normalized.get("project"))
    normalized["pack"] = _coerce_mapping(normalized.get("pack"))
    normalized["data"] = _coerce_mapping(normalized.get("data"))
    normalized["objective"] = _coerce_mapping(normalized.get("objective"))
    normalized["search"] = _coerce_mapping(normalized.get("search"))
    normalized["evaluation"] = _coerce_mapping(normalized.get("evaluation"))
    normalized["constraints"] = _coerce_mapping(normalized.get("constraints"))
    normalized["runtime"] = _coerce_mapping(normalized.get("runtime"))
    normalized["outputs"] = _coerce_mapping(normalized.get("outputs"))
    normalized["pack_config"] = _coerce_mapping(normalized.get("pack_config"))
    normalized["search"].setdefault("editable_targets", ["workspace/strategy.py"])
    normalized["search"].setdefault("allowed_axes", [])
    normalized["runtime"].setdefault("env_refs", [])
    normalized["runtime"].setdefault("secret_refs", [])
    normalized["objective"].setdefault("secondary", [])
    normalized["objective"].setdefault("stop_when", {})
    normalized["data"].setdefault("schema_map", {})
    normalized["data"].setdefault("filters", {})
    normalized["data"].setdefault("sampling", {})
    normalized["data"].setdefault("split", {})
    normalized["evaluation"].setdefault("gate_overrides", {})
    return normalized


def _ensure_type(errors: list[str], field: str, value: Any, expected_type: type) -> None:
    if not isinstance(value, expected_type):
        errors.append(f"{field} must be {expected_type.__name__}")


def _ensure_str(errors: list[str], field: str, value: Any, *, allow_empty: bool = False) -> str:
    _ensure_type(errors, field, value, str)
    if isinstance(value, str) and not allow_empty and not value.strip():
        errors.append(f"{field} must not be empty")
    return str(value) if isinstance(value, str) else ""


def _ensure_bool(errors: list[str], field: str, value: Any) -> None:
    if not isinstance(value, bool):
        errors.append(f"{field} must be bool")


def _ensure_int(errors: list[str], field: str, value: Any, *, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{field} must be int")
        return
    if value < minimum or value > maximum:
        errors.append(f"{field} must be between {minimum} and {maximum}")


def _ensure_float(errors: list[str], field: str, value: Any, *, minimum: float, maximum: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{field} must be number")
        return
    if float(value) < minimum or float(value) > maximum:
        errors.append(f"{field} must be between {minimum} and {maximum}")


def _list_of_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, str) for item in value):
        return None
    return value


def validate_research_spec(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_research_spec(payload)
    errors: list[str] = []

    _ensure_str(errors, "schema_version", normalized.get("schema_version"))
    if normalized.get("schema_version") != "research.yaml.v1":
        errors.append("schema_version must be research.yaml.v1")

    project = normalized["project"]
    pack = normalized["pack"]
    data = normalized["data"]
    objective = normalized["objective"]
    search = normalized["search"]
    evaluation = normalized["evaluation"]
    constraints = normalized["constraints"]
    runtime = normalized["runtime"]
    outputs = normalized["outputs"]
    pack_config = normalized["pack_config"]

    _ensure_str(errors, "project.name", project.get("name"))
    _ensure_str(errors, "project.workspace_dir", project.get("workspace_dir"))
    _ensure_str(errors, "project.artifacts_dir", project.get("artifacts_dir"))
    _ensure_str(errors, "project.runs_dir", project.get("runs_dir"))

    _ensure_str(errors, "pack.id", pack.get("id"))
    _ensure_str(errors, "pack.version", pack.get("version"), allow_empty=True)
    _ensure_str(errors, "pack.entry_profile", pack.get("entry_profile"))

    _ensure_str(errors, "data.source", data.get("source"))
    _ensure_str(errors, "data.format", data.get("format"))
    _ensure_str(errors, "data.adapter", data.get("adapter"))
    _ensure_bool(errors, "data.snapshot_on_run", data.get("snapshot_on_run"))
    _ensure_type(errors, "data.schema_map", data.get("schema_map"), dict)
    _ensure_type(errors, "data.filters", data.get("filters"), dict)

    sampling = _coerce_mapping(data.get("sampling"))
    split = _coerce_mapping(data.get("split"))
    _ensure_str(errors, "data.sampling.mode", sampling.get("mode"))
    _ensure_int(errors, "data.sampling.max_records", sampling.get("max_records"), minimum=1, maximum=1_000_000)
    _ensure_int(errors, "data.sampling.seed", sampling.get("seed"), minimum=0, maximum=2**31 - 1)
    _ensure_str(errors, "data.split.mode", split.get("mode"))
    for field in ("train_ratio", "validation_ratio", "holdout_ratio"):
        if split.get(field) is not None:
            _ensure_float(errors, f"data.split.{field}", split.get(field), minimum=0.0, maximum=1.0)

    _ensure_str(errors, "objective.primary", objective.get("primary"))
    secondary = _list_of_strings(objective.get("secondary"))
    if secondary is None:
        errors.append("objective.secondary must be list[str]")
    direction = objective.get("direction")
    _ensure_str(errors, "objective.direction", direction)
    if direction not in {"maximize", "minimize"}:
        errors.append("objective.direction must be maximize or minimize")
    stop_when = _coerce_mapping(objective.get("stop_when"))
    _ensure_str(errors, "objective.stop_when.metric", stop_when.get("metric"), allow_empty=True)
    if stop_when.get("threshold") is not None and not isinstance(stop_when.get("threshold"), (int, float)):
        errors.append("objective.stop_when.threshold must be number or null")
    _ensure_str(errors, "objective.notes", objective.get("notes"), allow_empty=True)

    editable_targets = _list_of_strings(search.get("editable_targets"))
    if not editable_targets:
        errors.append("search.editable_targets must be non-empty list[str]")
    allowed_axes = _list_of_strings(search.get("allowed_axes"))
    if not allowed_axes:
        errors.append("search.allowed_axes must be non-empty list[str]")
    frozen_axes = _list_of_strings(search.get("frozen_axes"))
    if frozen_axes is None:
        errors.append("search.frozen_axes must be list[str]")
    _ensure_str(errors, "search.mode", search.get("mode"))
    _ensure_int(errors, "search.max_iterations", search.get("max_iterations"), minimum=1, maximum=1000)
    _ensure_int(errors, "search.candidates_per_iteration", search.get("candidates_per_iteration"), minimum=1, maximum=100)
    _ensure_str(errors, "search.mutation_policy", search.get("mutation_policy"))
    _ensure_bool(errors, "search.allow_prompt_edits", search.get("allow_prompt_edits"))
    _ensure_bool(errors, "search.allow_feature_edits", search.get("allow_feature_edits"))
    _ensure_bool(errors, "search.allow_risk_edits", search.get("allow_risk_edits"))

    _ensure_int(errors, "evaluation.sample_size", evaluation.get("sample_size"), minimum=1, maximum=1_000_000)
    _ensure_int(errors, "evaluation.search_repeats", evaluation.get("search_repeats"), minimum=1, maximum=100)
    _ensure_int(errors, "evaluation.validation_repeats", evaluation.get("validation_repeats"), minimum=1, maximum=100)
    _ensure_int(errors, "evaluation.holdout_repeats", evaluation.get("holdout_repeats"), minimum=1, maximum=100)
    _ensure_str(errors, "evaluation.gate_profile", evaluation.get("gate_profile"))
    _ensure_type(errors, "evaluation.gate_overrides", evaluation.get("gate_overrides"), dict)
    _ensure_bool(errors, "evaluation.emit_breakdowns", evaluation.get("emit_breakdowns"))

    _ensure_int(errors, "constraints.total_token_budget", constraints.get("total_token_budget"), minimum=0, maximum=50_000_000)
    _ensure_int(errors, "constraints.per_eval_token_budget", constraints.get("per_eval_token_budget"), minimum=1, maximum=5_000_000)
    _ensure_int(errors, "constraints.max_completion_tokens", constraints.get("max_completion_tokens"), minimum=1, maximum=32_000)
    _ensure_int(errors, "constraints.eval_timeout_seconds", constraints.get("eval_timeout_seconds"), minimum=1, maximum=86_400)
    _ensure_int(errors, "constraints.max_runtime_minutes", constraints.get("max_runtime_minutes"), minimum=0, maximum=10_080)
    _ensure_int(errors, "constraints.max_memory_mb", constraints.get("max_memory_mb"), minimum=1, maximum=262_144)
    _ensure_int(errors, "constraints.max_cpu_seconds", constraints.get("max_cpu_seconds"), minimum=1, maximum=86_400)
    _ensure_bool(errors, "constraints.allow_network", constraints.get("allow_network"))
    _ensure_bool(errors, "constraints.real_execution", constraints.get("real_execution"))
    _ensure_bool(errors, "constraints.preserve_run", constraints.get("preserve_run"))
    _ensure_int(errors, "constraints.retention_hours", constraints.get("retention_hours"), minimum=1, maximum=24 * 365)

    _ensure_str(errors, "runtime.provider", runtime.get("provider"))
    _ensure_str(errors, "runtime.model", runtime.get("model"))
    _ensure_str(errors, "runtime.api_base_url", runtime.get("api_base_url"), allow_empty=True)
    env_refs = _list_of_strings(runtime.get("env_refs"))
    if env_refs is None:
        errors.append("runtime.env_refs must be list[str]")
    secret_refs = _list_of_strings(runtime.get("secret_refs"))
    if secret_refs is None:
        errors.append("runtime.secret_refs must be list[str]")
    _ensure_int(errors, "runtime.concurrency", runtime.get("concurrency"), minimum=1, maximum=64)

    _ensure_bool(errors, "outputs.write_patch", outputs.get("write_patch"))
    _ensure_bool(errors, "outputs.write_report", outputs.get("write_report"))
    _ensure_bool(errors, "outputs.write_dataset_profile", outputs.get("write_dataset_profile"))
    _ensure_bool(errors, "outputs.write_best_strategy", outputs.get("write_best_strategy"))
    _ensure_str(errors, "outputs.export_format", outputs.get("export_format"))
    if outputs.get("export_format") not in {"json", "yaml", "both"}:
        errors.append("outputs.export_format must be one of: json, yaml, both")

    _ensure_type(errors, "pack_config", pack_config, dict)

    if isinstance(split, dict):
        def _ratio_value(name: str) -> float:
            value = split.get(name, 0.0)
            if value in {None, ""}:
                return 0.0
            return float(value)

        ratios = [
            _ratio_value("train_ratio"),
            _ratio_value("validation_ratio"),
            _ratio_value("holdout_ratio"),
        ]
        if all(value >= 0 for value in ratios) and sum(ratios) > 0:
            total = round(sum(ratios), 6)
            if abs(total - 1.0) > 0.01:
                errors.append("data.split ratios must sum to 1.0")

    if errors:
        raise ResearchSpecError("invalid research spec: " + "; ".join(errors))
    return normalized


def load_research_spec(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = load_yaml_text(text)
    return validate_research_spec(payload)


def write_research_spec(path: str | Path, spec: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_research_yaml(spec), encoding="utf-8")
    return target
