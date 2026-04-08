from __future__ import annotations

import random
from statistics import median
from typing import Any, Callable


PACK_ID = "prediction_market"
DEFAULT_INITIAL_BANKROLL = 10000
DEFAULT_BET_UNIT = 100
DEFAULT_SAMPLE_SIZE = 200
DEFAULT_RANDOM_SEED = 42

EVALUATOR_SPEC = {
    "objective": "maximize_pnl",
    "secondary_objectives": ["maximize_accuracy", "minimize_drawdown"],
    "metrics": [
        "fitness",
        "total_pnl",
        "accuracy",
        "max_drawdown",
        "num_trades",
        "num_skipped",
        "win_rate",
        "avg_pnl_per_trade",
        "sharpe_ratio",
    ],
}


def load_eval_markets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(records)


def sample_eval_markets(
    records: list[dict[str, Any]],
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_RANDOM_SEED,
) -> list[dict[str, Any]]:
    if not records:
        return []
    rng = random.Random(seed)
    sorted_records = sorted(records, key=lambda item: float(item.get("volume", 0.0)), reverse=True)
    third = max(1, len(sorted_records) // 3)
    high = sorted_records[:third]
    mid = sorted_records[third : 2 * third]
    low = sorted_records[2 * third :]
    per_tier = sample_size // 3
    remainder = sample_size - per_tier * 3
    sampled: list[dict[str, Any]] = []
    if high:
        sampled.extend(rng.sample(high, min(per_tier + remainder, len(high))))
    if mid:
        sampled.extend(rng.sample(mid, min(per_tier, len(mid))))
    if low:
        sampled.extend(rng.sample(low, min(per_tier, len(low))))
    rng.shuffle(sampled)
    return sampled[:sample_size]


def calculate_pnl(bet: dict[str, Any], market: dict[str, Any]) -> float:
    if bet.get("action") == "skip":
        return 0.0
    outcome_idx = int(bet.get("outcome_index", 0))
    size = float(bet.get("size", 0.0))
    winning_idx = int(market.get("final_resolution_index", 0))
    last_price = float(market.get("last_trade_price", 0.0))
    entry_price = last_price if outcome_idx == 0 else 1.0 - last_price
    entry_price = max(0.01, min(0.99, entry_price))
    if bet.get("action") == "buy":
        return size * (1.0 - entry_price) / entry_price if outcome_idx == winning_idx else -size
    if bet.get("action") == "sell":
        return size * entry_price / (1.0 - entry_price) if outcome_idx != winning_idx else -size
    return 0.0


def evaluate_strategy(
    strategy_func: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    records: list[dict[str, Any]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_RANDOM_SEED,
    initial_bankroll: float = DEFAULT_INITIAL_BANKROLL,
    verbose: bool = False,
) -> dict[str, Any]:
    markets = sample_eval_markets(records, sample_size=sample_size, seed=seed)
    bankroll = float(initial_bankroll)
    peak_bankroll = float(initial_bankroll)
    max_drawdown = 0.0
    pnl_list: list[float] = []
    correct = 0
    total_trades = 0
    skipped = 0

    for index, market in enumerate(markets):
        try:
            bet = strategy_func(market)
        except Exception as exc:  # pragma: no cover - strategy errors are expected by contract
            if verbose:
                print(f"strategy error at market {market.get('market_id', index)}: {exc}")
            bet = {"action": "skip", "outcome_index": 0, "size": 0, "confidence": 0}
        if bet.get("action") == "skip":
            skipped += 1
            continue
        max_bet = bankroll * 0.2
        bet["size"] = min(float(bet.get("size", 0.0)), max_bet)
        if bet["size"] <= 0:
            skipped += 1
            continue
        pnl = calculate_pnl(bet, market)
        pnl_list.append(pnl)
        bankroll += pnl
        total_trades += 1
        if pnl > 0:
            correct += 1
        peak_bankroll = max(peak_bankroll, bankroll)
        drawdown = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    total_pnl = bankroll - initial_bankroll
    accuracy = correct / max(1, total_trades)
    win_rate = accuracy
    avg_pnl = total_pnl / max(1, total_trades)
    if len(pnl_list) > 1:
        mean_pnl = sum(pnl_list) / len(pnl_list)
        variance = sum((item - mean_pnl) ** 2 for item in pnl_list) / (len(pnl_list) - 1)
        sharpe = mean_pnl / (variance ** 0.5) if variance > 0 else 0.0
    else:
        sharpe = 0.0
    normalized_pnl = total_pnl / initial_bankroll if initial_bankroll else 0.0
    fitness = normalized_pnl + 10 * accuracy - 5 * max_drawdown
    return {
        "fitness": round(fitness, 6),
        "total_pnl": round(total_pnl, 2),
        "accuracy": round(accuracy, 4),
        "max_drawdown": round(max_drawdown, 4),
        "num_trades": total_trades,
        "num_skipped": skipped,
        "win_rate": round(win_rate, 4),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "sharpe_ratio": round(sharpe, 4),
        "final_bankroll": round(bankroll, 2),
    }


def summarize_market_profile(records: list[dict[str, Any]]) -> dict[str, Any]:
    volumes = [float(item.get("volume", 0.0)) for item in records]
    categories: dict[str, int] = {}
    for item in records:
        category = str((item.get("context") or {}).get("category", "unknown") or "unknown")
        categories[category] = categories.get(category, 0) + 1
    return {
        "num_records": len(records),
        "categories": dict(sorted(categories.items(), key=lambda pair: (-pair[1], pair[0]))),
        "volume_min": round(min(volumes), 2) if volumes else 0.0,
        "volume_median": round(median(volumes), 2) if volumes else 0.0,
        "volume_max": round(max(volumes), 2) if volumes else 0.0,
    }
