from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _parse_jsonish(value: str, default: Any) -> Any:
    if value in ("", None):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normalize_record(row: dict[str, Any], index: int) -> dict[str, Any]:
    outcomes = row.get("outcomes", [])
    if isinstance(outcomes, str):
        outcomes = _parse_jsonish(outcomes, [])
    outcome_prices = row.get("outcome_prices", [])
    if isinstance(outcome_prices, str):
        outcome_prices = _parse_jsonish(outcome_prices, [])
    price_signals = row.get("price_signals", {})
    if isinstance(price_signals, str):
        price_signals = _parse_jsonish(price_signals, {})
    context = row.get("context", {})
    if isinstance(context, str):
        context = _parse_jsonish(context, {})
    if not isinstance(context, dict):
        context = {}

    final_resolution_index = int(_parse_float(row.get("final_resolution_index", 0), 0))
    final_resolution = str(row.get("final_resolution", "") or "")
    if not final_resolution and isinstance(outcomes, list) and 0 <= final_resolution_index < len(outcomes):
        final_resolution = str(outcomes[final_resolution_index])

    normalized_context = {
        "category": str(context.get("category", row.get("category", "unknown")) or "unknown"),
        "subcategory": str(context.get("subcategory", row.get("subcategory", "")) or ""),
        "event_title": str(context.get("event_title", row.get("event_title", "")) or ""),
        "liquidity": max(0.0, _parse_float(context.get("liquidity", row.get("liquidity", 0.0)))),
        "neg_risk": _parse_bool(context.get("neg_risk", row.get("neg_risk", False))),
    }

    return {
        "market_id": str(row.get("market_id", "") or f"row-{index}"),
        "question": str(row.get("question", "")),
        "outcomes": [str(item) for item in outcomes] if isinstance(outcomes, list) else [],
        "outcome_prices": [_parse_float(item) for item in outcome_prices] if isinstance(outcome_prices, list) else [],
        "final_resolution": final_resolution,
        "final_resolution_index": final_resolution_index,
        "last_trade_price": _parse_float(row.get("last_trade_price", row.get("lastTradePrice", 0.0))),
        "price_signals": price_signals if isinstance(price_signals, dict) else {},
        "volume": max(0.0, _parse_float(row.get("volume", row.get("volumeNum", 0.0)))),
        "context": normalized_context,
    }


def normalize_dataset_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(records, start=1):
        if isinstance(item, dict):
            normalized.append(_normalize_record(item, index))
    return normalized


def load_dataset_records(source: str | Path) -> list[dict[str, Any]]:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("records"), list):
            payload = payload["records"]
        if not isinstance(payload, list):
            raise ValueError("JSON dataset must be a list or {\"records\": [...]}")
        return normalize_dataset_records([item for item in payload if isinstance(item, dict)])

    if suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return normalize_dataset_records([item for item in rows if isinstance(item, dict)])

    if suffix == ".csv":
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        return normalize_dataset_records(rows)

    raise ValueError("unsupported dataset format; expected .json, .jsonl, or .csv")
