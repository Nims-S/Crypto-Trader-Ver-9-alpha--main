from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from .diversity import DEFAULT_FAMILY_QUOTAS, DEFAULT_SYMBOL_QUOTAS, build_generation_quota_plan

REGIME_FAMILY_BIAS = {
    "trend": {
        "trend": 1.35,
        "mean_reversion": 0.78,
        "volatility_compression": 0.98,
    },
    "mean_reversion": {
        "mean_reversion": 1.35,
        "volatility_compression": 1.05,
        "trend": 0.72,
    },
    "volatility_compression": {
        "volatility_compression": 1.45,
        "mean_reversion": 0.92,
        "trend": 0.82,
    },
    "adaptive": {
        "mean_reversion": 1.05,
        "volatility_compression": 1.0,
        "trend": 0.95,
    },
}

REGIME_SYMBOL_BIAS = {
    "trend": {
        "BTC/USDT": 1.10,
        "ETH/USDT": 1.05,
        "SOL/USDT": 1.08,
    },
    "mean_reversion": {
        "BTC/USDT": 1.15,
        "ETH/USDT": 1.10,
        "SOL/USDT": 0.95,
    },
    "volatility_compression": {
        "BTC/USDT": 1.00,
        "ETH/USDT": 1.18,
        "SOL/USDT": 1.12,
    },
    "adaptive": {
        "BTC/USDT": 1.0,
        "ETH/USDT": 1.0,
        "SOL/USDT": 1.0,
    },
}


@dataclass(slots=True)
class RegimeQuotaReport:
    regime: str
    family_quotas: dict[str, int]
    symbol_quotas: dict[str, int]
    plan: list[dict[str, Any]]
    history_size: int
    dominant_family: str
    dominant_symbol: str
    dominant_regime: str
    adaptive_multiplier: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)



def _symbol_root(symbol: str) -> str:
    symbol = str(symbol or "").upper()
    return symbol.split("/")[0] if symbol else "UNKNOWN"



def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def _weighted_round(base: int, multiplier: float) -> int:
    return max(0, int(round(base * multiplier)))



def _dominant_key(counter: Counter[str]) -> str:
    if not counter:
        return "unknown"
    return max(counter.items(), key=lambda item: (item[1], item[0]))[0]



def infer_regime(candidates: list[dict[str, Any]] | None = None, *, fallback: str = "adaptive") -> str:
    if not candidates:
        return fallback

    regime_counter: Counter[str] = Counter()
    family_counter: Counter[str] = Counter()
    symbol_counter: Counter[str] = Counter()

    for row in candidates:
        if not isinstance(row, dict):
            continue
        regime = str(row.get("regime") or "adaptive").lower()
        family = str(row.get("family") or "unknown").lower()
        symbol = _symbol_root(str(row.get("symbol") or ""))
        regime_counter[regime] += 1
        family_counter[family] += 1
        symbol_counter[symbol] += 1

    dominant_regime = _dominant_key(regime_counter)
    if dominant_regime in REGIME_FAMILY_BIAS:
        return dominant_regime

    if family_counter.get("mean_reversion", 0) >= family_counter.get("trend", 0) + 1:
        return "mean_reversion"
    if family_counter.get("volatility_compression", 0) >= family_counter.get("trend", 0):
        return "volatility_compression"
    return fallback



def tune_family_quotas(
    regime: str,
    *,
    family_quotas: dict[str, int] | None = None,
    candidate_history: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    base = dict(DEFAULT_FAMILY_QUOTAS)
    if family_quotas:
        for key, value in family_quotas.items():
            base[key] = max(0, int(value))

    normalized_regime = str(regime or "adaptive").lower()
    bias = REGIME_FAMILY_BIAS.get(normalized_regime, REGIME_FAMILY_BIAS["adaptive"])

    if candidate_history:
        family_scores: defaultdict[str, list[float]] = defaultdict(list)
        for row in candidate_history:
            if not isinstance(row, dict):
                continue
            family = str(row.get("family") or "unknown").lower()
            score = _as_float(row.get("validation_score"), 0.0)
            if score <= 0.0:
                score = _as_float(row.get("robustness_score"), 0.0)
            if score > 0.0:
                family_scores[family].append(score)
        if family_scores:
            best_family = max(
                family_scores.items(),
                key=lambda item: (mean(item[1]), len(item[1]), item[0]),
            )[0]
            bias = dict(bias)
            bias[best_family] = bias.get(best_family, 1.0) + 0.15

    tuned = {
        family: _weighted_round(base.get(family, 0), bias.get(family, 1.0))
        for family in base
    }

    for family, count in tuned.items():
        if base.get(family, 0) > 0 and count == 0:
            tuned[family] = 1

    return tuned



def tune_symbol_quotas(
    regime: str,
    *,
    symbol_quotas: dict[str, int] | None = None,
    candidate_history: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    base = dict(DEFAULT_SYMBOL_QUOTAS)
    if symbol_quotas:
        for key, value in symbol_quotas.items():
            base[key] = max(0, int(value))

    normalized_regime = str(regime or "adaptive").lower()
    bias = REGIME_SYMBOL_BIAS.get(normalized_regime, REGIME_SYMBOL_BIAS["adaptive"])

    if candidate_history:
        symbol_scores: defaultdict[str, list[float]] = defaultdict(list)
        for row in candidate_history:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            score = _as_float(row.get("validation_score"), 0.0)
            if score <= 0.0:
                score = _as_float(row.get("robustness_score"), 0.0)
            if score > 0.0:
                symbol_scores[symbol].append(score)
        if symbol_scores:
            best_symbol = max(
                symbol_scores.items(),
                key=lambda item: (mean(item[1]), len(item[1]), item[0]),
            )[0]
            bias = dict(bias)
            bias[best_symbol] = bias.get(best_symbol, 1.0) + 0.10

    tuned = {
        symbol: _weighted_round(base.get(symbol, 0), bias.get(symbol, 1.0))
        for symbol in base
    }

    for symbol, count in tuned.items():
        if base.get(symbol, 0) > 0 and count == 0:
            tuned[symbol] = 1

    return tuned



def build_regime_quota_plan(
    iterations: int,
    *,
    regime: str = "adaptive",
    family_quotas: dict[str, int] | None = None,
    symbol_quotas: dict[str, int] | None = None,
    candidate_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    tuned_families = tune_family_quotas(
        regime,
        family_quotas=family_quotas,
        candidate_history=candidate_history,
    )
    tuned_symbols = tune_symbol_quotas(
        regime,
        symbol_quotas=symbol_quotas,
        candidate_history=candidate_history,
    )
    from .generation import DEFAULT_FAMILIES, DEFAULT_SYMBOLS

    return build_generation_quota_plan(
        iterations,
        DEFAULT_FAMILIES,
        DEFAULT_SYMBOLS,
        family_quota=tuned_families,
        symbol_quota=tuned_symbols,
    )



def regime_quota_report(
    iterations: int,
    *,
    regime: str = "adaptive",
    candidate_history: list[dict[str, Any]] | None = None,
    family_quotas: dict[str, int] | None = None,
    symbol_quotas: dict[str, int] | None = None,
) -> RegimeQuotaReport:
    plan = build_regime_quota_plan(
        iterations,
        regime=regime,
        family_quotas=family_quotas,
        symbol_quotas=symbol_quotas,
        candidate_history=candidate_history,
    )
    family_counts = Counter(item["family"] for item in plan)
    symbol_counts = Counter(item["symbol"] for item in plan)
    dominant_family = _dominant_key(family_counts)
    dominant_symbol = _dominant_key(symbol_counts)
    dominant_regime = infer_regime(candidate_history, fallback=regime)
    adaptive_multiplier = 1.0
    if dominant_regime == "trend":
        adaptive_multiplier = 1.15
    elif dominant_regime == "mean_reversion":
        adaptive_multiplier = 1.12
    elif dominant_regime == "volatility_compression":
        adaptive_multiplier = 1.18

    return RegimeQuotaReport(
        regime=regime,
        family_quotas=tune_family_quotas(
            regime,
            family_quotas=family_quotas,
            candidate_history=candidate_history,
        ),
        symbol_quotas=tune_symbol_quotas(
            regime,
            symbol_quotas=symbol_quotas,
            candidate_history=candidate_history,
        ),
        plan=plan,
        history_size=len(candidate_history or []),
        dominant_family=dominant_family,
        dominant_symbol=dominant_symbol,
        dominant_regime=dominant_regime,
        adaptive_multiplier=round(adaptive_multiplier, 4),
    )
