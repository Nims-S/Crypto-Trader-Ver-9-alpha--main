from __future__ import annotations

from dataclasses import dataclass

from .search import OptimizationCandidate


@dataclass(slots=True)
class GuardrailDecision:
    accepted: bool
    reason: str


class OptimizationGuardrails:
    """
    Anti-overfitting safety filters.

    Purpose:
    - reject unstable candidates
    - prevent optimization pathology
    - reduce curve-fit risk
    - enforce minimum statistical quality
    """

    def __init__(
        self,
        *,
        min_trade_count: int = 30,
        max_drawdown_pct: float = 35.0,
        min_sharpe_ratio: float = 0.5,
        max_return_to_drawdown_ratio: float = 8.0,
    ) -> None:
        self.min_trade_count = min_trade_count
        self.max_drawdown_pct = max_drawdown_pct
        self.min_sharpe_ratio = min_sharpe_ratio
        self.max_return_to_drawdown_ratio = (
            max_return_to_drawdown_ratio
        )

    def evaluate(
        self,
        candidate: OptimizationCandidate,
    ) -> GuardrailDecision:
        metrics = candidate.metrics

        trade_count = int(
            metrics.get("trade_count", 0)
        )

        drawdown = abs(
            float(metrics.get("max_drawdown_pct", 0.0))
        )

        sharpe = float(
            metrics.get("sharpe_ratio", 0.0)
        )

        total_return = float(
            metrics.get("total_return_pct", 0.0)
        )

        if trade_count < self.min_trade_count:
            return GuardrailDecision(
                accepted=False,
                reason="insufficient_trade_count",
            )

        if drawdown > self.max_drawdown_pct:
            return GuardrailDecision(
                accepted=False,
                reason="excessive_drawdown",
            )

        if sharpe < self.min_sharpe_ratio:
            return GuardrailDecision(
                accepted=False,
                reason="weak_sharpe_ratio",
            )

        if drawdown > 0:
            ratio = total_return / drawdown

            if ratio > self.max_return_to_drawdown_ratio:
                return GuardrailDecision(
                    accepted=False,
                    reason="suspicious_return_profile",
                )

        return GuardrailDecision(
            accepted=True,
            reason="accepted",
        )
