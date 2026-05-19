from __future__ import annotations

from dataclasses import dataclass, field

from ..strategies.base import Strategy
from .classifier import RegimeState


@dataclass(slots=True)
class RoutedStrategy:
    strategy_id: str
    enabled: bool
    weight_multiplier: float
    reason: str


@dataclass(slots=True)
class RegimeRoutingDecision:
    timestamp: str
    active_regimes: dict[str, str]
    routed_strategies: list[RoutedStrategy] = field(default_factory=list)


class StrategyRegimeRouter:
    """
    Primitive regime-aware strategy gating.

    Purpose:
    - prevent strategies from trading in hostile regimes
    - reduce unconditional exposure
    - establish future adaptive allocation framework
    """

    def route(
        self,
        *,
        strategies: list[Strategy],
        regime: RegimeState,
    ) -> RegimeRoutingDecision:
        routed: list[RoutedStrategy] = []

        for strategy in strategies:
            enabled = True
            weight_multiplier = 1.0
            reason = "default"

            family = getattr(strategy, "family", "unknown")

            if family == "trend_following":
                if regime.trend_regime == "sideways":
                    enabled = False
                    weight_multiplier = 0.0
                    reason = "disabled_in_sideways_market"

                elif regime.volatility_regime == "extreme_volatility":
                    enabled = True
                    weight_multiplier = 0.5
                    reason = "reduced_size_extreme_volatility"

            elif family == "ml_pattern_matching":
                if regime.volatility_regime == "extreme_volatility":
                    enabled = False
                    weight_multiplier = 0.0
                    reason = "ml_disabled_extreme_volatility"

                elif regime.liquidity_regime == "low_liquidity":
                    enabled = True
                    weight_multiplier = 0.4
                    reason = "reduced_size_low_liquidity"

            routed.append(
                RoutedStrategy(
                    strategy_id=strategy.strategy_id,
                    enabled=enabled,
                    weight_multiplier=weight_multiplier,
                    reason=reason,
                )
            )

        return RegimeRoutingDecision(
            timestamp=regime.timestamp,
            active_regimes={
                "volatility": regime.volatility_regime,
                "trend": regime.trend_regime,
                "liquidity": regime.liquidity_regime,
            },
            routed_strategies=routed,
        )
