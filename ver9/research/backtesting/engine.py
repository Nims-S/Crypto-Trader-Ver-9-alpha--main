from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..strategies.base import Signal, Strategy


@dataclass(slots=True)
class Trade:
    timestamp: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    fees: float
    slippage_bps: float


@dataclass(slots=True)
class BacktestResult:
    strategy_id: str
    symbol: str
    timeframe: str

    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float

    trade_count: int

    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    def __init__(
        self,
        *,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
        initial_capital: float = 10000.0,
    ) -> None:
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.initial_capital = initial_capital

    def run(
        self,
        *,
        strategy: Strategy,
        frame: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> BacktestResult:
        signals = strategy.generate_signals(frame)

        if not signals:
            return BacktestResult(
                strategy_id=strategy.strategy_id,
                symbol=symbol,
                timeframe=timeframe,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                trade_count=0,
            )

        capital = self.initial_capital
        peak_equity = capital
        wins = 0

        trades: list[Trade] = []
        equity_curve: list[float] = [capital]

        for signal in signals:
            candle = frame.loc[
                frame["timestamp"].astype(str) == signal.timestamp
            ]

            if candle.empty:
                continue

            close_price = float(candle.iloc[0]["close"])

            entry_price = close_price * (1 + (self.slippage_bps / 10000.0))
            exit_price = close_price * 1.002

            gross_pnl = (exit_price - entry_price)
            fees = entry_price * (self.fee_bps / 10000.0)
            net_pnl = gross_pnl - fees

            capital += net_pnl
            peak_equity = max(peak_equity, capital)

            if net_pnl > 0:
                wins += 1

            equity_curve.append(capital)

            trades.append(
                Trade(
                    timestamp=signal.timestamp,
                    symbol=symbol,
                    side=signal.side,
                    quantity=1.0,
                    entry_price=round(entry_price, 4),
                    exit_price=round(exit_price, 4),
                    pnl=round(net_pnl, 4),
                    fees=round(fees, 4),
                    slippage_bps=self.slippage_bps,
                )
            )

        total_return_pct = (
            (capital - self.initial_capital)
            / self.initial_capital
        ) * 100.0

        max_drawdown_pct = (
            (min(equity_curve) - peak_equity)
            / peak_equity
        ) * 100.0

        returns = pd.Series(equity_curve).pct_change().dropna()

        sharpe = (
            (returns.mean() / returns.std()) * (252**0.5)
            if not returns.empty and returns.std() > 0
            else 0.0
        )

        win_rate = (wins / len(trades)) if trades else 0.0

        return BacktestResult(
            strategy_id=strategy.strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=round(max_drawdown_pct, 4),
            sharpe_ratio=round(float(sharpe), 4),
            win_rate=round(win_rate, 4),
            trade_count=len(trades),
            trades=trades,
            equity_curve=[round(x, 4) for x in equity_curve],
        )
