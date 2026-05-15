from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

ALLOWED_STATUSES = {"validated", "probationary", "deployable", "live"}

FAMILY_MULTIPLIERS = {
    "mean_reversion": 1.12,
    "volatility_compression": 1.08,
    "trend": 0.95,
    "hybrid": 1.0,
}

REGIME_MULTIPLIERS = {
    "mean_reversion": 1.08,
    "volatility_compression": 1.04,
    "trend": 1.0,
    "adaptive": 1.0,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _symbol_root(symbol: str) -> str:
    symbol = str(symbol or "").upper()
    return symbol.split("/")[0] if symbol else "UNKNOWN"


@dataclass(slots=True)
class BasketSelection:
    selected: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    basket_score: float = 0.0
    diversity_score: float = 0.0
    correlation_penalty: float = 0.0
    probationary: bool = False
    max_positions: int = 3
    min_positions: int = 2

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_allocations(self) -> list[dict[str, Any]]:
        allocations: list[dict[str, Any]] = []
        for row in self.selected:
            strategy_id = str(row.get("strategy_id") or row.get("candidate_id") or "unknown")
            weight = _to_float(self.weights.get(strategy_id), 0.0)
            allocations.append(
                {
                    "strategy_id": strategy_id,
                    "symbol": row.get("symbol"),
                    "family": row.get("family"),
                    "regime": row.get("regime"),
                    "status": row.get("status"),
                    "allocation_pct": round(weight, 6),
                    "allocation_weight": round(weight, 6),
                    "basket_score": round(_to_float(row.get("basket_score"), 0.0), 4),
                    "candidate_score": round(_to_float(row.get("candidate_score"), 0.0), 4),
                    "probationary": self.probationary,
                }
            )
        return allocations


class BasketOptimizer:
    def __init__(
        self,
        *,
        max_positions: int = 3,
        min_positions: int = 2,
        soft_fill: bool = True,
        enforce_unique_symbols: bool = True,
        enforce_unique_families: bool = False,
        min_candidate_score: float = 0.2,
    ) -> None:
        self.max_positions = max(1, int(max_positions))
        self.min_positions = max(1, int(min_positions))
        self.soft_fill = bool(soft_fill)
        self.enforce_unique_symbols = bool(enforce_unique_symbols)
        self.enforce_unique_families = bool(enforce_unique_families)
        self.min_candidate_score = float(min_candidate_score)

    def candidate_score(self, candidate: dict[str, Any]) -> float:
        pf = max(_to_float(candidate.get("profit_factor"), 0.0), 0.0)
        ret = _to_float(candidate.get("return_pct"), 0.0)
        dd = abs(_to_float(candidate.get("max_drawdown_pct"), 0.0))
        robustness = _to_float(candidate.get("robustness_score"), 0.0)
        trades = max(int(_to_float(candidate.get("trades"), 0.0)), 0)

        validation = candidate.get("validation") or {}
        evidence = candidate.get("strategy_evidence") or validation.get("evidence") or {}
        wf = validation.get("walk_forward") or {}
        mc = validation.get("monte_carlo") or {}
        pt = validation.get("perturbation") or {}
        xs = validation.get("cross_symbol") or {}

        validation_boost = 0.0
        validation_boost += 0.40 if wf.get("passed") else 0.0
        validation_boost += 0.45 if mc.get("passed") else 0.0
        validation_boost += 0.35 if pt.get("passed") else 0.0
        validation_boost += 0.35 if xs.get("passed") else 0.0
        validation_boost += _to_float(evidence.get("walk_forward_score"), 0.0) * 0.12
        validation_boost += _to_float(evidence.get("monte_carlo_score"), 0.0) * 0.18
        validation_boost += _to_float(evidence.get("perturbation_score"), 0.0) * 0.16
        validation_boost += _to_float(evidence.get("cross_symbol_score"), 0.0) * 0.16

        family = str(candidate.get("family") or "unknown").lower()
        regime = str(candidate.get("regime") or "adaptive").lower()
        family_mult = FAMILY_MULTIPLIERS.get(family, 1.0)
        regime_mult = REGIME_MULTIPLIERS.get(regime, 1.0)

        base = (
            (pf * 2.5)
            + max(ret, 0.0) / 9.0
            + (robustness * 5.0)
            + (min(trades, 400) / 400.0) * 0.8
            + validation_boost
        )
        score = (base * family_mult * regime_mult) / max(dd, 1.0)
        return round(score, 6)

    def _pair_penalty(self, candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
        penalty = 0.0
        candidate_symbol = _symbol_root(str(candidate.get("symbol") or ""))
        candidate_family = str(candidate.get("family") or "unknown").lower()
        candidate_regime = str(candidate.get("regime") or "adaptive").lower()
        candidate_timeframe = str(candidate.get("timeframe") or "unknown").lower()

        for row in selected:
            selected_symbol = _symbol_root(str(row.get("symbol") or ""))
            selected_family = str(row.get("family") or "unknown").lower()
            selected_regime = str(row.get("regime") or "adaptive").lower()
            selected_timeframe = str(row.get("timeframe") or "unknown").lower()

            if candidate_symbol == selected_symbol:
                penalty += 1.75
            if candidate_family == selected_family:
                penalty += 0.55
            if candidate_regime == selected_regime:
                penalty += 0.30
            if candidate_timeframe == selected_timeframe:
                penalty += 0.10

            correlation_hint = _to_float(candidate.get("correlation_hint"), 0.0)
            if correlation_hint:
                penalty += abs(correlation_hint) * 0.25
            correlation_hint = _to_float(row.get("correlation_hint"), 0.0)
            if correlation_hint:
                penalty += abs(correlation_hint) * 0.15

        return round(penalty, 6)

    def _diversity_bonus(self, candidate: dict[str, Any], selected: list[dict[str, Any]]) -> float:
        if not selected:
            return 0.15

        bonus = 0.0
        candidate_symbol = _symbol_root(str(candidate.get("symbol") or ""))
        candidate_family = str(candidate.get("family") or "unknown").lower()
        candidate_regime = str(candidate.get("regime") or "adaptive").lower()
        candidate_timeframe = str(candidate.get("timeframe") or "unknown").lower()

        if candidate_symbol not in {_symbol_root(str(row.get("symbol") or "")) for row in selected}:
            bonus += 0.35
        if candidate_family not in {str(row.get("family") or "unknown").lower() for row in selected}:
            bonus += 0.15
        if candidate_regime not in {str(row.get("regime") or "adaptive").lower() for row in selected}:
            bonus += 0.10
        if candidate_timeframe not in {str(row.get("timeframe") or "unknown").lower() for row in selected}:
            bonus += 0.05
        return round(bonus, 6)

    def _is_eligible(self, candidate: dict[str, Any]) -> bool:
        status = str(candidate.get("status") or "").lower()
        if status not in ALLOWED_STATUSES:
            return False
        if candidate.get("validation_passed") is False:
            return False
        if _to_float(candidate.get("validation_score"), 0.0) <= 0.0 and _to_float(candidate.get("robustness_score"), 0.0) <= 0.0:
            return False
        return True

    def build(self, candidates: list[dict[str, Any]]) -> BasketSelection:
        eligible = [dict(candidate) for candidate in candidates if isinstance(candidate, dict) and self._is_eligible(candidate)]
        ranked = sorted(eligible, key=self.candidate_score, reverse=True)

        selected: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        selected_ids: set[str] = set()
        selected_symbols: set[str] = set()
        selected_families: set[str] = set()
        selected_regimes: set[str] = set()

        def consider(row: dict[str, Any], *, relaxed: bool = False) -> bool:
            strategy_id = str(row.get("strategy_id") or row.get("candidate_id") or "unknown")
            symbol = _symbol_root(str(row.get("symbol") or ""))
            family = str(row.get("family") or "unknown").lower()
            regime = str(row.get("regime") or "adaptive").lower()
            candidate_score = self.candidate_score(row)
            pair_penalty = self._pair_penalty(row, selected)
            diversity_bonus = self._diversity_bonus(row, selected)
            basket_score = round(candidate_score + diversity_bonus - pair_penalty, 6)

            row["candidate_score"] = candidate_score
            row["basket_score"] = basket_score
            row["diversity_bonus"] = diversity_bonus
            row["pair_penalty"] = pair_penalty

            if strategy_id in selected_ids:
                rejected.append({"strategy_id": strategy_id, "reason": "duplicate_strategy"})
                return False

            if self.enforce_unique_symbols and symbol in selected_symbols and not relaxed:
                rejected.append({"strategy_id": strategy_id, "reason": "duplicate_symbol"})
                return False

            if self.enforce_unique_families and family in selected_families and not relaxed:
                rejected.append({"strategy_id": strategy_id, "reason": "duplicate_family"})
                return False

            if basket_score < self.min_candidate_score and len(selected) >= self.min_positions and not relaxed:
                rejected.append({"strategy_id": strategy_id, "reason": "score_below_threshold"})
                return False

            if basket_score < 0.0 and not selected:
                rejected.append({"strategy_id": strategy_id, "reason": "negative_seed_score"})
                return False

            selected.append(row)
            selected_ids.add(strategy_id)
            selected_symbols.add(symbol)
            selected_families.add(family)
            selected_regimes.add(regime)
            return True

        for row in ranked:
            if len(selected) >= self.max_positions:
                break
            consider(row, relaxed=False)

        if self.soft_fill and len(selected) < self.min_positions:
            for row in ranked:
                if len(selected) >= self.max_positions:
                    break
                consider(row, relaxed=True)

        if not selected:
            return BasketSelection(
                selected=[],
                rejected=rejected,
                weights={},
                basket_score=0.0,
                diversity_score=0.0,
                correlation_penalty=0.0,
                probationary=True,
                max_positions=self.max_positions,
                min_positions=self.min_positions,
            )

        basket_scores = [max(_to_float(row.get("basket_score"), 0.0), 0.0) for row in selected]
        total_score = sum(basket_scores)
        if total_score <= 0:
            weight = 1.0 / len(selected)
            weights = {
                str(row.get("strategy_id") or row.get("candidate_id") or "unknown"): weight
                for row in selected
            }
        else:
            weights = {
                str(row.get("strategy_id") or row.get("candidate_id") or "unknown"): round(score / total_score, 6)
                for row, score in zip(selected, basket_scores, strict=False)
            }

        unique_symbol_count = len({ _symbol_root(str(row.get("symbol") or "")) for row in selected })
        unique_family_count = len({ str(row.get("family") or "unknown").lower() for row in selected })
        unique_regime_count = len({ str(row.get("regime") or "adaptive").lower() for row in selected })
        diversity_score = round((unique_symbol_count + unique_family_count + unique_regime_count) / 3.0, 6)
        correlation_penalty = round(sum(row.get("pair_penalty", 0.0) for row in selected), 6)
        basket_score = round(mean(basket_scores) if basket_scores else 0.0, 6)
        probationary = len(selected) < self.min_positions

        return BasketSelection(
            selected=selected,
            rejected=rejected,
            weights=weights,
            basket_score=basket_score,
            diversity_score=diversity_score,
            correlation_penalty=correlation_penalty,
            probationary=probationary,
            max_positions=self.max_positions,
            min_positions=self.min_positions,
        )

    def allocate(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        basket = self.build(candidates)
        allocations = basket.as_allocations()
        if not allocations:
            return []
        return allocations


def build_basket(candidates: list[dict[str, Any]], *, max_positions: int = 3, min_positions: int = 2, soft_fill: bool = True) -> BasketSelection:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=soft_fill,
    )
    return optimizer.build(candidates)


def basket_summary(candidates: list[dict[str, Any]], *, max_positions: int = 3, min_positions: int = 2, soft_fill: bool = True) -> dict[str, Any]:
    basket = build_basket(candidates, max_positions=max_positions, min_positions=min_positions, soft_fill=soft_fill)
    return basket.as_dict()