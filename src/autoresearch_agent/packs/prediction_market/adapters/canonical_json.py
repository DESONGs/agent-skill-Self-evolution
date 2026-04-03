from __future__ import annotations

from typing import Any


ADAPTER_ID = "canonical_json"
SUPPORTED_INPUT_FORMATS = ["json"]


def normalize_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        payload = payload["records"]
    if not isinstance(payload, list):
        raise ValueError("canonical_json expects a list of records or {\"records\": [...]} payload")
    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("canonical_json records must be objects")
        records.append(dict(item))
    return records
