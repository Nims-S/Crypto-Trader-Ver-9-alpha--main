from __future__ import annotations

from .models import ProtectionDecision


class ProtectionEngine:
    def __init__(
        self,
        *,
        max_drawdown_pct: float = -15.0,
        max_loss_streak: int = 4,
        volatility_throttle: float = 0.9,
    ) -> None:
        self.max_drawdown_pct = max_drawdown_pct
        self.max_loss_streak = max_loss_streak
        self.volatility_throttle = volatility_throttle

    def evaluate(
        self,
        *,
        portfolio_drawdown_pct: float,
        rolling_loss_streak: int,
        volatility_regime_score: float,
    ) -> ProtectionDecision:
        if portfolio_drawdown_pct <= self.max_drawdown_pct:
            return ProtectionDecision(
                approved=False,
                reason="portfolio_drawdown_limit",
                cooldown_minutes=240,
                capital_multiplier=0.0,
            )

        if rolling_loss_streak >= self.max_loss_streak:
            return ProtectionDecision(
                approved=False,
                reason="loss_streak_cooldown",
                cooldown_minutes=120,
                capital_multiplier=0.0,
            )

        if volatility_regime_score >= self.volatility_throttle:
            return ProtectionDecision(
                approved=True,
                reason="volatility_throttle",
                cooldown_minutes=0,
                capital_multiplier=0.5,
            )

        return ProtectionDecision(
            approved=True,
            reason="approved",
            cooldown_minutes=0,
            capital_multiplier=1.0,
        )
