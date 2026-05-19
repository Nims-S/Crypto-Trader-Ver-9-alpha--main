from __future__ import annotations

from dataclasses import dataclass

from ..backtesting.engine import BacktestResult


@dataclass(slots=True)
class PerformanceReport:
    strategy_id: str
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    trade_count: int



def build_report(result: BacktestResult) -> PerformanceReport:
    return PerformanceReport(
        strategy_id=result.strategy_id,
        total_return_pct=result.total_return_pct,
        max_drawdown_pct=result.max_drawdown_pct,
        sharpe_ratio=result.sharpe_ratio,
        win_rate=result.win_rate,
        trade_count=result.trade_count,
    )
