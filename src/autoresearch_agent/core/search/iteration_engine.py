from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import statistics

from .gate_policy import GatePolicy, evaluate_gate
from .mutation_policy import MutationPolicy, mutate_config


StrategyFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def _default_strategy(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    threshold = float(config.get("confidence_threshold", 0.75) or 0.75)
    predicted = 0 if float(record.get("last_trade_price", 0.0) or 0.0) >= threshold else 1
    confidence = abs(float(record.get("last_trade_price", 0.0) or 0.0) - 0.5) * 2
    action = "buy"
    outcome_index = predicted
    size = float(config.get("max_bet_fraction", 0.15) or 0.15)
    return {
        "action": action,
        "outcome_index": outcome_index,
        "size": size,
        "prediction": predicted,
        "confidence": round(min(1.0, max(0.0, confidence)), 4),
    }


def _calculate_pnl(bet: dict[str, Any], record: dict[str, Any]) -> float:
    if bet.get("action") == "skip":
        return 0.0

    outcome_idx = int(bet.get("outcome_index", 0) or 0)
    size = float(bet.get("size", 0.0) or 0.0)
    last_price = float(record.get("last_trade_price", 0.0) or 0.0)
    winning_idx = int(record.get("final_resolution_index", 0) or 0)
    entry_price = last_price if outcome_idx == 0 else 1.0 - last_price
    entry_price = max(0.01, min(0.99, entry_price))

    if bet.get("action") == "buy":
        return size * (1.0 - entry_price) / entry_price if outcome_idx == winning_idx else -size
    if bet.get("action") == "sell":
        return size * entry_price / (1.0 - entry_price) if outcome_idx != winning_idx else -size
    return 0.0


def evaluate_prediction_market_strategy(
    records: list[dict[str, Any]],
    config: dict[str, Any],
    strategy_fn: StrategyFn | None = None,
) -> dict[str, Any]:
    if not records:
        return {
            "fitness": 0.0,
            "total_pnl": 0.0,
            "accuracy": 0.0,
            "max_drawdown": 0.0,
            "num_trades": 0,
            "num_skipped": 0,
            "win_rate": 0.0,
            "avg_pnl_per_trade": 0.0,
            "final_bankroll": 10000.0,
        }

    strategy = strategy_fn or _default_strategy
    bankroll = 10000.0
    peak_bankroll = bankroll
    max_drawdown = 0.0
    pnl_list: list[float] = []
    correct = 0
    trades = 0
    skipped = 0

    for record in records:
        bet = strategy(record, config)
        if bet.get("action") == "skip":
            skipped += 1
            continue

        bet = dict(bet)
        max_bet = bankroll * 0.2
        bet["size"] = min(float(bet.get("size", 0.0) or 0.0), max_bet)
        if bet["size"] <= 0:
            skipped += 1
            continue

        pnl = _calculate_pnl(bet, record)
        pnl_list.append(pnl)
        bankroll += pnl
        trades += 1
        if pnl > 0:
            correct += 1
        peak_bankroll = max(peak_bankroll, bankroll)
        drawdown = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    total_pnl = bankroll - 10000.0
    accuracy = correct / max(1, trades)
    avg_pnl = total_pnl / max(1, trades)
    normalized_pnl = total_pnl / 10000.0
    fitness = normalized_pnl + 10 * accuracy - 5 * max_drawdown
    sharpe = 0.0
    if len(pnl_list) > 1:
        std = statistics.stdev(pnl_list)
        sharpe = statistics.mean(pnl_list) / std if std > 0 else 0.0

    return {
        "fitness": round(fitness, 6),
        "total_pnl": round(total_pnl, 2),
        "accuracy": round(accuracy, 4),
        "max_drawdown": round(max_drawdown, 4),
        "num_trades": trades,
        "num_skipped": skipped,
        "win_rate": round(accuracy, 4),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "sharpe_ratio": round(sharpe, 4),
        "final_bankroll": round(bankroll, 2),
        "prediction_threshold": round(float(config.get("confidence_threshold", 0.75) or 0.75), 4),
        "max_bet_fraction": round(float(config.get("max_bet_fraction", 0.15) or 0.15), 4),
    }


@dataclass
class IterationEngine:
    gate_policy: GatePolicy = field(default_factory=GatePolicy)
    mutation_policy: MutationPolicy = field(default_factory=MutationPolicy)

    def run(
        self,
        records: list[dict[str, Any]],
        config: dict[str, Any],
        *,
        max_iterations: int = 1,
        strategy_fn: StrategyFn | None = None,
    ) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        current = dict(config)
        best_result: dict[str, Any] | None = None
        best_config = dict(current)

        for iteration in range(1, max(1, max_iterations) + 1):
            metrics = evaluate_prediction_market_strategy(records, current, strategy_fn=strategy_fn)
            history.append({"iteration": iteration, "config": dict(current), "metrics": metrics})
            if best_result is None or metrics["fitness"] > best_result["fitness"]:
                best_result = metrics
                best_config = dict(current)
            current = mutate_config(current, metrics, self.mutation_policy)
            if current == history[-1]["config"]:
                break

        best_result = best_result or evaluate_prediction_market_strategy(records, current, strategy_fn=strategy_fn)
        accepted, gate_metrics = evaluate_gate(best_result, {"fitness": 0.0, "max_drawdown": 1.0, "accuracy": 0.0}, self.gate_policy)
        return {
            "history": history,
            "best_config": best_config,
            "best_result": best_result,
            "gate_passed": accepted,
            "gate_metrics": gate_metrics,
        }
