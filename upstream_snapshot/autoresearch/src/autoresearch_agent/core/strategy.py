from __future__ import annotations

import difflib
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .artifacts.writers import write_text


StrategyCallable = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

CONFIG_DEFAULTS = {
    "confidence_threshold": 0.75,
    "bet_sizing": "confidence_scaled",
    "max_bet_fraction": 0.15,
    "prompt_factors": [],
}

FIELD_MAP = {
    "CONFIDENCE_THRESHOLD": "confidence_threshold",
    "BET_SIZING": "bet_sizing",
    "MAX_BET_FRACTION": "max_bet_fraction",
    "PROMPT_FACTORS": "prompt_factors",
}

REVERSE_FIELD_MAP = {value: key for key, value in FIELD_MAP.items()}


@dataclass(frozen=True)
class LoadedStrategy:
    path: Path
    source_text: str
    config: dict[str, Any]
    strategy_fn: StrategyCallable


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("autoresearch_workspace_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load strategy module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _coerce_config_value(name: str, value: Any) -> Any:
    if name == "prompt_factors":
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if isinstance(item, str)]
    if name == "bet_sizing":
        return str(value or CONFIG_DEFAULTS[name])
    return float(value if value is not None else CONFIG_DEFAULTS[name])


def extract_strategy_config(module: ModuleType) -> dict[str, Any]:
    config = dict(CONFIG_DEFAULTS)
    for constant_name, runtime_name in FIELD_MAP.items():
        if hasattr(module, constant_name):
            config[runtime_name] = _coerce_config_value(runtime_name, getattr(module, constant_name))
    return config


def _fallback_strategy(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    threshold = float(config.get("confidence_threshold", CONFIG_DEFAULTS["confidence_threshold"]) or CONFIG_DEFAULTS["confidence_threshold"])
    max_fraction = float(config.get("max_bet_fraction", CONFIG_DEFAULTS["max_bet_fraction"]) or CONFIG_DEFAULTS["max_bet_fraction"])
    price = float(record.get("last_trade_price", 0.0) or 0.0)
    predicted = 0 if price >= threshold else 1
    confidence = round(min(1.0, max(0.0, abs(price - 0.5) * 2)), 4)
    sizing = str(config.get("bet_sizing", CONFIG_DEFAULTS["bet_sizing"]) or CONFIG_DEFAULTS["bet_sizing"])
    if sizing == "fixed":
        size = max_fraction
    elif sizing == "kelly":
        size = max_fraction * max(0.1, confidence * confidence)
    else:
        size = max_fraction * max(0.25, confidence)
    return {
        "action": "buy",
        "outcome_index": predicted,
        "size": round(max(0.0, min(max_fraction, size)), 4),
        "prediction": predicted,
        "confidence": confidence,
    }


def _normalize_strategy_result(result: dict[str, Any], record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)
    action = str(normalized.get("action", "buy") or "buy")
    if action == "skip":
        normalized.setdefault("outcome_index", 0)
        normalized.setdefault("prediction", 0)
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("size", 0.0)
        return normalized

    price = float(record.get("last_trade_price", 0.0) or 0.0)
    prediction = normalized.get("prediction", normalized.get("outcome_index", 0))
    try:
        prediction = int(prediction)
    except (TypeError, ValueError):
        prediction = 0 if price >= float(config.get("confidence_threshold", CONFIG_DEFAULTS["confidence_threshold"]) or CONFIG_DEFAULTS["confidence_threshold"]) else 1

    confidence = normalized.get("confidence")
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = round(min(1.0, max(0.0, abs(price - 0.5) * 2)), 4)

    size = normalized.get("size")
    if size is None:
        size = _fallback_strategy(record, config)["size"]

    normalized["action"] = action
    normalized["prediction"] = prediction
    normalized["outcome_index"] = int(normalized.get("outcome_index", prediction) or prediction)
    normalized["confidence"] = round(min(1.0, max(0.0, confidence_value)), 4)
    normalized["size"] = round(max(0.0, float(size)), 4)
    return normalized


def _wrap_strategy(module: ModuleType) -> StrategyCallable:
    raw = getattr(module, "strategy", None)
    if not callable(raw):
        return _fallback_strategy

    def wrapped(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        try:
            result = raw(record, config)
        except TypeError:
            result = raw(record)
        if not isinstance(result, dict):
            raise TypeError("strategy(record, config) must return dict")
        return _normalize_strategy_result(result, record, config)

    return wrapped


def load_strategy(strategy_path: Path) -> LoadedStrategy:
    strategy_path = strategy_path.resolve()
    module = _load_module(strategy_path)
    source_text = strategy_path.read_text(encoding="utf-8")
    return LoadedStrategy(
        path=strategy_path,
        source_text=source_text,
        config=extract_strategy_config(module),
        strategy_fn=_wrap_strategy(module),
    )


def _render_scalar(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def apply_config_to_strategy_text(source_text: str, config: dict[str, Any]) -> str:
    updated = source_text
    for runtime_name, value in config.items():
        constant_name = REVERSE_FIELD_MAP.get(runtime_name)
        if not constant_name:
            continue
        rendered = _render_scalar(value)
        pattern = rf"^{constant_name}\s*=\s*.*$"
        replacement = f"{constant_name} = {rendered}"
        updated, count = re.subn(pattern, replacement, updated, count=1, flags=re.MULTILINE)
        if count == 0:
            updated = f"{replacement}\n{updated}"
    return updated


def build_strategy_patch(original_text: str, updated_text: str, path_label: str = "workspace/strategy.py") -> str:
    return "".join(
        difflib.unified_diff(
            original_text.splitlines(keepends=True),
            updated_text.splitlines(keepends=True),
            fromfile=path_label,
            tofile=path_label,
        )
    )


def write_strategy_artifacts(
    run_dir: Path,
    original_text: str,
    best_config: dict[str, Any],
    *,
    write_best_strategy: bool = True,
    write_patch: bool = True,
) -> dict[str, Path]:
    artifacts_dir = run_dir / "artifacts"
    best_text = apply_config_to_strategy_text(original_text, best_config)
    patch_text = build_strategy_patch(original_text, best_text)
    written: dict[str, Path] = {}
    if write_best_strategy:
        best_strategy_path = artifacts_dir / "best_strategy.py"
        write_text(best_strategy_path, best_text)
        written["best_strategy"] = best_strategy_path
    if write_patch:
        patch_path = artifacts_dir / "strategy.patch"
        write_text(patch_path, patch_text)
        written["patch"] = patch_path
    return written
