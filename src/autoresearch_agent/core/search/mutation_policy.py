from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MutationPolicy:
    confidence_step: float = 0.02
    bet_fraction_step: float = 0.01


def mutate_config(config: dict[str, Any], metrics: dict[str, Any], policy: MutationPolicy) -> dict[str, Any]:
    updated = dict(config)
    accuracy = float(metrics.get("accuracy", 0.0) or 0.0)
    drawdown = float(metrics.get("max_drawdown", 0.0) or 0.0)

    threshold = float(updated.get("confidence_threshold", 0.75) or 0.75)
    bet_fraction = float(updated.get("max_bet_fraction", 0.15) or 0.15)

    if accuracy < 0.5:
        threshold = max(0.45, threshold - policy.confidence_step)
        bet_fraction = max(0.05, bet_fraction - policy.bet_fraction_step)
    elif drawdown > 0.2:
        threshold = min(0.9, threshold + policy.confidence_step)
        bet_fraction = max(0.05, bet_fraction - policy.bet_fraction_step)
    else:
        threshold = min(0.9, threshold + policy.confidence_step / 2)

    updated["confidence_threshold"] = round(threshold, 4)
    updated["max_bet_fraction"] = round(bet_fraction, 4)
    return updated
