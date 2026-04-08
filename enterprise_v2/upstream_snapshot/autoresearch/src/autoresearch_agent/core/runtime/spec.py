from __future__ import annotations

from pathlib import Path
from typing import Any
import copy
import ast
import json


class RuntimeSpecError(ValueError):
    pass


DEFAULT_RUNTIME_SPEC: dict[str, Any] = {
    "schema_version": "research.yaml.v1",
    "project": {
        "name": "autoresearch-project",
        "workspace_dir": "./workspace",
        "artifacts_dir": "./artifacts",
        "runs_dir": "./.autoresearch/runs",
    },
    "pack": {
        "id": "prediction_market",
        "version": "latest",
        "entry_profile": "default",
    },
    "data": {
        "source": "./datasets/eval_markets.json",
        "format": "auto",
        "adapter": "auto",
        "snapshot_on_run": True,
        "sampling": {
            "mode": "fixed_count",
            "max_records": 200,
            "seed": 42,
        },
    },
    "objective": {
        "primary": "maximize_pnl",
        "secondary": ["maximize_accuracy", "minimize_drawdown"],
        "direction": "maximize",
    },
    "search": {
        "mode": "self_iterate",
        "editable_targets": ["workspace/strategy.py"],
        "allowed_axes": ["prompt_factors", "confidence_threshold", "bet_sizing", "max_bet_fraction"],
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
        "per_eval_token_budget": 150000,
        "max_completion_tokens": 1200,
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


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def normalize_runtime_spec(payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _merge_dict(DEFAULT_RUNTIME_SPEC, payload or {})
    normalized["data"] = _merge_dict(DEFAULT_RUNTIME_SPEC["data"], normalized.get("data", {}))
    normalized["search"] = _merge_dict(DEFAULT_RUNTIME_SPEC["search"], normalized.get("search", {}))
    normalized["evaluation"] = _merge_dict(DEFAULT_RUNTIME_SPEC["evaluation"], normalized.get("evaluation", {}))
    normalized["constraints"] = _merge_dict(DEFAULT_RUNTIME_SPEC["constraints"], normalized.get("constraints", {}))
    normalized["runtime"] = _merge_dict(DEFAULT_RUNTIME_SPEC["runtime"], normalized.get("runtime", {}))
    normalized["outputs"] = _merge_dict(DEFAULT_RUNTIME_SPEC["outputs"], normalized.get("outputs", {}))
    normalized.setdefault("pack_config", {})
    return normalized


def _ensure_type(errors: list[str], field: str, value: Any, expected_type: type) -> None:
    if not isinstance(value, expected_type):
        errors.append(f"{field} must be {expected_type.__name__}")


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line.rstrip()
    in_quote = False
    quote = ""
    for index, char in enumerate(line):
        if char in {'"', "'"}:
            if not in_quote:
                in_quote = True
                quote = char
            elif quote == char:
                in_quote = False
        elif char == "#" and not in_quote:
            return line[:index].rstrip()
    return line.rstrip()


def _parse_scalar(text: str) -> Any:
    value = text.strip()
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if value.startswith(("[", "{")):
        try:
            return json.loads(value.replace("'", '"'))
        except Exception:
            try:
                return ast.literal_eval(value)
            except Exception:
                return value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        try:
            return json.loads(value)
        except Exception:
            return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_significant_line(lines: list[str], start: int) -> tuple[int | None, str | None, int | None]:
    for index in range(start, len(lines)):
        stripped = _strip_comment(lines[index]).strip()
        if stripped:
            return index, stripped, _leading_spaces(lines[index])
    return None, None, None


def _parse_yaml_text(text: str) -> dict[str, Any]:
    lines = text.splitlines()

    def parse_block(start: int, indent: int) -> tuple[Any, int]:
        index, stripped, current_indent = _next_significant_line(lines, start)
        if index is None or stripped is None or current_indent is None or current_indent < indent:
            return {}, start
        if stripped.startswith("- "):
            container: Any = []
        else:
            container = {}

        i = index
        while i < len(lines):
            raw = _strip_comment(lines[i])
            if not raw.strip():
                i += 1
                continue
            line_indent = _leading_spaces(lines[i])
            line = raw.strip()
            if line_indent < indent:
                break
            if line_indent > indent:
                raise RuntimeError("invalid yaml indentation")

            if isinstance(container, list):
                if not line.startswith("- "):
                    break
                item_text = line[2:].strip()
                i += 1
                if item_text:
                    container.append(_parse_scalar(item_text))
                    continue
                child, i = parse_block(i, indent + 2)
                container.append(child)
                continue

            if line.startswith("- "):
                break
            if ":" not in line:
                raise RuntimeError(f"invalid yaml mapping line: {line}")
            key, raw_value = line.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            i += 1
            if raw_value:
                container[key] = _parse_scalar(raw_value)
                continue

            next_index, next_stripped, next_indent = _next_significant_line(lines, i)
            if next_index is None or next_stripped is None or next_indent is None or next_indent <= indent:
                container[key] = {}
                continue
            child, i = parse_block(next_index, next_indent)
            container[key] = child

        return container, i

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise RuntimeError("top-level yaml document must be a mapping")
    return parsed


def validate_runtime_spec(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_runtime_spec(payload)
    errors: list[str] = []

    _ensure_type(errors, "schema_version", normalized.get("schema_version"), str)
    for field in ("project", "pack", "data", "objective", "search", "evaluation", "constraints", "runtime", "outputs"):
        _ensure_type(errors, field, normalized.get(field), dict)

    if not str(normalized.get("schema_version", "")).strip():
        errors.append("schema_version is required")

    project = normalized.get("project", {})
    for field in ("name", "workspace_dir", "artifacts_dir", "runs_dir"):
        if field == "name":
            _ensure_type(errors, f"project.{field}", project.get(field), str)
        elif field in project:
            _ensure_type(errors, f"project.{field}", project.get(field), str)

    pack = normalized.get("pack", {})
    _ensure_type(errors, "pack.id", pack.get("id"), str)

    data = normalized.get("data", {})
    _ensure_type(errors, "data.source", data.get("source"), str)
    _ensure_type(errors, "data.adapter", data.get("adapter"), str)

    search = normalized.get("search", {})
    editable_targets = search.get("editable_targets", [])
    if not isinstance(editable_targets, list) or not editable_targets or any(not isinstance(item, str) for item in editable_targets):
        errors.append("search.editable_targets must be a non-empty list[str]")

    allowed_axes = search.get("allowed_axes", [])
    if not isinstance(allowed_axes, list) or any(not isinstance(item, str) for item in allowed_axes):
        errors.append("search.allowed_axes must be list[str]")

    evaluation = normalized.get("evaluation", {})
    for field in ("sample_size", "search_repeats", "validation_repeats", "holdout_repeats"):
        if field in evaluation and not isinstance(evaluation.get(field), int):
            errors.append(f"evaluation.{field} must be int")

    constraints = normalized.get("constraints", {})
    for field in ("total_token_budget", "per_eval_token_budget", "max_completion_tokens", "eval_timeout_seconds", "max_runtime_minutes", "max_memory_mb", "max_cpu_seconds", "retention_hours"):
        if field in constraints and not isinstance(constraints.get(field), int):
            errors.append(f"constraints.{field} must be int")
    for field in ("allow_network", "real_execution", "preserve_run"):
        if field in constraints and not isinstance(constraints.get(field), bool):
            errors.append(f"constraints.{field} must be bool")

    runtime = normalized.get("runtime", {})
    _ensure_type(errors, "runtime.provider", runtime.get("provider"), str)
    _ensure_type(errors, "runtime.model", runtime.get("model"), str)
    if not isinstance(runtime.get("env_refs", []), list) or any(not isinstance(item, str) for item in runtime.get("env_refs", [])):
        errors.append("runtime.env_refs must be list[str]")
    if not isinstance(runtime.get("secret_refs", []), list) or any(not isinstance(item, str) for item in runtime.get("secret_refs", [])):
        errors.append("runtime.secret_refs must be list[str]")

    outputs = normalized.get("outputs", {})
    for field in ("write_patch", "write_report", "write_dataset_profile", "write_best_strategy"):
        if field in outputs and not isinstance(outputs.get(field), bool):
            errors.append(f"outputs.{field} must be bool")
    _ensure_type(errors, "outputs.export_format", outputs.get("export_format"), str)

    if errors:
        raise RuntimeSpecError("invalid runtime spec: " + "; ".join(errors))
    return normalized


def load_runtime_spec(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = _parse_yaml_text(text)
    if not isinstance(payload, dict):
        raise RuntimeSpecError("runtime spec must be a JSON object")
    return validate_runtime_spec(payload)
