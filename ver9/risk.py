from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class DriftSignal:
    strategy_id: str
    live_return_pct: float
    expected_return_pct: float
    live_drawdown_pct: float
    expected_drawdown_pct: float
    return_gap_pct: float
    drawdown_gap_pct: float
    quarantine: bool
    throttle: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PortfolioRiskState:
    portfolio_drawdown_pct: float
    rolling_loss_streak: int
    volatility_regime_score: float
    approved: bool
    capital_multiplier: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class RiskMonitor:
    def __init__(
        self,
        *,
        max_return_gap_pct: float = -25.0,
        max_drawdown_gap_pct: float = 8.0,
        portfolio_quarantine_drawdown_pct: float = -15.0,
        portfolio_loss_streak_limit: int = 4,
    ) -> None:
        self.max_return_gap_pct = max_return_gap_pct
        self.max_drawdown_gap_pct = max_drawdown_gap_pct
        self.portfolio_quarantine_drawdown_pct = portfolio_quarantine_drawdown_pct
        self.portfolio_loss_streak_limit = portfolio_loss_streak_limit

    def evaluate_drift(self, *, strategy_id: str, live_metrics: dict[str, Any], expected_metrics: dict[str, Any]) -> DriftSignal:
        live_return = float(live_metrics.get("return_pct") or live_metrics.get("pnl_pct") or 0.0)
        expected_return = float(expected_metrics.get("return_pct") or expected_metrics.get("pnl_pct") or 0.0)
        live_drawdown = abs(float(live_metrics.get("max_drawdown_pct") or live_metrics.get("drawdown_pct") or 0.0))
        expected_drawdown = abs(float(expected_metrics.get("max_drawdown_pct") or expected_metrics.get("drawdown_pct") or 0.0))

        return_gap = live_return - expected_return
        drawdown_gap = live_drawdown - expected_drawdown

        quarantine = return_gap <= self.max_return_gap_pct or drawdown_gap >= self.max_drawdown_gap_pct
        throttle = (return_gap <= -10.0) or (drawdown_gap >= 4.0)
        reason = "ok"
        if quarantine:
            reason = "drift_quarantine"
        elif throttle:
            reason = "drift_throttle"

        return DriftSignal(
            strategy_id=strategy_id,
            live_return_pct=round(live_return, 4),
            expected_return_pct=round(expected_return, 4),
            live_drawdown_pct=round(live_drawdown, 4),
            expected_drawdown_pct=round(expected_drawdown, 4),
            return_gap_pct=round(return_gap, 4),
            drawdown_gap_pct=round(drawdown_gap, 4),
            quarantine=quarantine,
            throttle=throttle,
            reason=reason,
        )

    def evaluate_portfolio(self, *, portfolio_drawdown_pct: float, rolling_loss_streak: int, volatility_regime_score: float) -> PortfolioRiskState:
        approved = True
        capital_multiplier = 1.0
        reason = "approved"

        if portfolio_drawdown_pct <= self.portfolio_quarantine_drawdown_pct:
            approved = False
            capital_multiplier = 0.0
            reason = "portfolio_quarantine"
        elif rolling_loss_streak >= self.portfolio_loss_streak_limit:
            approved = False
            capital_multiplier = 0.0
            reason = "loss_streak_quarantine"
        elif volatility_regime_score >= 0.9:
            capital_multiplier = 0.5
            reason = "volatility_throttle"

        return PortfolioRiskState(
            portfolio_drawdown_pct=round(portfolio_drawdown_pct, 4),
            rolling_loss_streak=int(rolling_loss_streak),
            volatility_regime_score=round(volatility_regime_score, 4),
            approved=approved,
            capital_multiplier=capital_multiplier,
            reason=reason,
        )
