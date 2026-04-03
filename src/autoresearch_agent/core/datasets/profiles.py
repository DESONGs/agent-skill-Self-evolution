from __future__ import annotations

from statistics import median
from typing import Any


def profile_dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    volumes = [float(record.get("volume", 0.0) or 0.0) for record in records]
    liquidities = [float((record.get("context") or {}).get("liquidity", 0.0) or 0.0) for record in records]
    categories: dict[str, int] = {}
    for record in records:
        category = str((record.get("context") or {}).get("category", "unknown") or "unknown")
        categories[category] = categories.get(category, 0) + 1

    return {
        "num_records": len(records),
        "categories": dict(sorted(categories.items(), key=lambda item: (-item[1], item[0]))),
        "volume_min": round(min(volumes), 2) if volumes else 0.0,
        "volume_median": round(median(volumes), 2) if volumes else 0.0,
        "volume_max": round(max(volumes), 2) if volumes else 0.0,
        "liquidity_median": round(median(liquidities), 2) if liquidities else 0.0,
    }
