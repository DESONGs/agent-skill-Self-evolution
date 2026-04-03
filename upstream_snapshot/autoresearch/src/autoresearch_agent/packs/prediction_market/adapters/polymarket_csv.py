from __future__ import annotations

import ast
import json
from typing import Any


ADAPTER_ID = "polymarket_csv"
SUPPORTED_INPUT_FORMATS = ["csv"]
MIN_VOLUME = 5000
RESOLUTION_THRESHOLD = 0.9


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value not in ("", None) else default
    except (TypeError, ValueError):
        return default


def _parse_json_list(value: str) -> list[Any] | None:
    if not value:
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        try:
            payload = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
    return payload if isinstance(payload, list) else None


def process_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("closed") != "True" or not row.get("resolvedBy"):
        return None
    volume = _parse_float(row.get("volumeNum", ""))
    if volume < MIN_VOLUME:
        return None
    outcomes = _parse_json_list(row.get("outcomes", ""))
    outcome_prices_raw = _parse_json_list(row.get("outcomePrices", ""))
    if not outcomes or not outcome_prices_raw or len(outcomes) != 2:
        return None
    outcome_prices = [_parse_float(value) for value in outcome_prices_raw]
    max_price = max(outcome_prices)
    if max_price < RESOLUTION_THRESHOLD:
        return None
    winner_index = outcome_prices.index(max_price)
    return {
        "market_id": row.get("id", ""),
        "question": row.get("question", ""),
        "outcomes": [str(item) for item in outcomes],
        "outcome_prices": outcome_prices,
        "final_resolution": str(outcomes[winner_index]),
        "final_resolution_index": winner_index,
        "last_trade_price": _parse_float(row.get("lastTradePrice", "")),
        "volume": volume,
        "context": {
            "category": row.get("category", "") or "unknown",
            "subcategory": row.get("subcategory", "") or "",
            "event_title": row.get("event_title", "") or "",
            "liquidity": _parse_float(row.get("liquidityNum", "")),
            "neg_risk": row.get("negRisk", "") == "True",
        },
    }
