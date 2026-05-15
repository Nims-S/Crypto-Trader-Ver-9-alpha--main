from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_FAMILY_QUOTAS = {
    "mean_reversion": 5,
    "volatility_compression": 4,
    "trend": 3,
}

DEFAULT_SYMBOL_QUOTAS = {
    "BTC/USDT": 4,
    "ETH/USDT": 4,
    "SOL/USDT": 3,
}


@dataclass(slots=True)
class DiversityReport:
    total_candidates: int
    unique_symbols: int
    unique_families: int
    unique_regimes: int
    symbol_counts: dict[str, int]
    family_counts: dict[str, int]
    regime_counts: dict[str, int]
    diversity_score: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _symbol_root(symbol: str) -> str:
    symbol = str(symbol or "").upper()
    return symbol.split("/")[0] if symbol else "UNKNOWN"


def normalize_quota_map(
    quota_map: dict[str, int] | None,
    items: list[str],
    *,
    default: int = 0,
) -> dict[str, int]:
    normalized: dict[str, int] = {}
    source = quota_map or {}
    for item in items:
        raw = source.get(item, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default
        normalized[item] = max(0, value)
    return normalized


def build_generation_quota_plan(
    iterations: int,
    families: list[str],
    symbols: list[str],
    *,
    family_quota: dict[str, int] | None = None,
    symbol_quota: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    iteration_cap = max(1, int(iterations))
    family_limits = normalize_quota_map(
        family_quota,
        families,
        default=iteration_cap,
    )
    symbol_limits = normalize_quota_map(
        symbol_quota,
        symbols,
        default=iteration_cap,
    )

    plan: list[dict[str, Any]] = []
    for family in families:
        for symbol in symbols:
            count = min(iteration_cap, family_limits.get(family, iteration_cap), symbol_limits.get(symbol, iteration_cap))
            if count <= 0:
                continue
            plan.append({"family": family, "symbol": symbol, "count": count})
    return plan


def diversity_report(candidates: list[dict[str, Any]]) -> DiversityReport:
    symbols = Counter(_symbol_root(str(row.get("symbol") or "")) for row in candidates if isinstance(row, dict))
    families = Counter(str(row.get("family") or "unknown").lower() for row in candidates if isinstance(row, dict))
    regimes = Counter(str(row.get("regime") or "adaptive").lower() for row in candidates if isinstance(row, dict))

    total = len(candidates)
    diversity = basket_diversity_score(candidates)
    return DiversityReport(
        total_candidates=total,
        unique_symbols=len(symbols),
        unique_families=len(families),
        unique_regimes=len(regimes),
        symbol_counts=dict(symbols),
        family_counts=dict(families),
        regime_counts=dict(regimes),
        diversity_score=diversity,
    )


def basket_diversity_score(candidates: list[dict[str, Any]]) -> float:
    if not candidates:
        return 0.0

    symbols = {_symbol_root(str(row.get("symbol") or "")) for row in candidates if isinstance(row, dict)}
    families = {str(row.get("family") or "unknown").lower() for row in candidates if isinstance(row, dict)}
    regimes = {str(row.get("regime") or "adaptive").lower() for row in candidates if isinstance(row, dict)}
    size = max(len(candidates), 1)
    score = ((len(symbols) * 1.4) + (len(families) * 1.1) + (len(regimes) * 0.9)) / size
    return round(score, 4)


def symbol_diversity_bonus(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    candidate_symbol = _symbol_root(str(candidate.get("symbol") or ""))
    selected_symbols = {_symbol_root(str(row.get("symbol") or "")) for row in selected if isinstance(row, dict)}
    if not selected:
        return 0.25
    return 0.4 if candidate_symbol not in selected_symbols else -0.15


def family_overlap_penalty(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    candidate_family = str(candidate.get("family") or "unknown").lower()
    overlap = sum(1 for row in selected if isinstance(row, dict) and str(row.get("family") or "unknown").lower() == candidate_family)
    return round(overlap * 0.35, 4)


def regime_overlap_penalty(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    candidate_regime = str(candidate.get("regime") or "adaptive").lower()
    overlap = sum(1 for row in selected if isinstance(row, dict) and str(row.get("regime") or "adaptive").lower() == candidate_regime)
    return round(overlap * 0.25, 4)


def correlation_penalty(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    penalty = abs(float(candidate.get("correlation_hint") or 0.0)) * 0.25
    for row in selected:
        if not isinstance(row, dict):
            continue
        penalty += abs(float(row.get("correlation_hint") or 0.0)) * 0.15
    return round(penalty, 4)


def combined_diversity_penalty(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    return round(
        family_overlap_penalty(candidate, selected)
        + regime_overlap_penalty(candidate, selected)
        + correlation_penalty(candidate, selected),
        4,
    )
