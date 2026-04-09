from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GatePolicy:
    min_fitness_delta: float = 0.0
    max_drawdown: float = 0.25
    min_accuracy: float = 0.0


def evaluate_gate(candidate: dict[str, Any], champion: dict[str, Any], policy: GatePolicy) -> tuple[bool, dict[str, float]]:
    delta_fitness = float(candidate.get("fitness", 0.0) or 0.0) - float(champion.get("fitness", 0.0) or 0.0)
    drawdown = float(candidate.get("max_drawdown", 0.0) or 0.0)
    accuracy = float(candidate.get("accuracy", 0.0) or 0.0)
    passed = delta_fitness >= policy.min_fitness_delta and drawdown <= policy.max_drawdown and accuracy >= policy.min_accuracy
    return passed, {
        "delta_fitness": round(delta_fitness, 6),
        "max_drawdown": round(drawdown, 6),
        "accuracy": round(accuracy, 6),
    }
