from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..strategies.base import Signal, Strategy


@dataclass(slots=True)
class Position:
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    entry_timestamp: str
    confidence: float


@dataclass(slots=True)
class PortfolioTrade:
    strategy_id: str
    symbol: str
    entry_timestamp: str
    exit_timestamp: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    net_pnl: float
    fees: float
    slippage_bps: float


@dataclass(slots=True)
class PortfolioBacktestResult:
    initial_capital: float
    ending_capital: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float

    total_trades: int
    winning_trades: int
    losing_trades: int

    active_strategies: list[str]
    symbol_exposure: dict[str, float]

    equity_curve: list[float] = field(default_factory=list)
    trades: list[PortfolioTrade] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PortfolioBacktestEngine:
    def __init__(
        self,
        *,
        initial_capital: float = 10000.0,
        max_positions: int = 5,
        max_symbol_exposure_pct: float = 0.35,
        risk_per_trade_pct: float = 0.02,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
        holding_period_bars: int = 4,
    ) -> None:
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.max_symbol_exposure_pct = max_symbol_exposure_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.holding_period_bars = holding_period_bars

    def _generate_strategy_signals(
        self,
        strategy: Strategy,
        frame: pd.DataFrame,
    ) -> list[Signal]:
        try:
            return strategy.generate_signals(frame)
        except Exception:
            return []

    def _current_symbol_exposure(
        self,
        positions: list[Position],
        symbol: str,
        capital: float,
    ) -> float:
        if capital <= 0:
            return 0.0

        exposure = sum(
            position.quantity * position.entry_price
            for position in positions
            if position.symbol == symbol
        )

        return exposure / capital

    def _calculate_position_size(
        self,
        capital: float,
        confidence: float,
        price: float,
    ) -> float:
        risk_budget = capital * self.risk_per_trade_pct

        confidence_multiplier = max(0.25, min(1.0, confidence))

        notional = risk_budget * confidence_multiplier

        if price <= 0:
            return 0.0

        return notional / price

    def run(
        self,
        *,
        strategies: list[Strategy],
        frame: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> PortfolioBacktestResult:
        working = frame.copy().reset_index(drop=True)

        strategy_signals: dict[str, list[Signal]] = {}

        for strategy in strategies:
            strategy_signals[strategy.strategy_id] = (
                self._generate_strategy_signals(strategy, working)
            )

        capital = self.initial_capital
        peak_equity = capital

        equity_curve: list[float] = [capital]
        positions: list[Position] = []
        trades: list[PortfolioTrade] = []

        symbol_exposure: dict[str, float] = {}

        timestamp_index = {
            str(row.timestamp): idx
            for idx, row in working.iterrows()
        }

        for strategy in strategies:
            signals = strategy_signals.get(strategy.strategy_id, [])

            for signal in signals:
                if len(positions) >= self.max_positions:
                    continue

                timestamp = str(signal.timestamp)

                if timestamp not in timestamp_index:
                    continue

                candle_idx = timestamp_index[timestamp]

                if candle_idx + self.holding_period_bars >= len(working):
                    continue

                entry_candle = working.iloc[candle_idx]
                exit_candle = working.iloc[
                    candle_idx + self.holding_period_bars
                ]

                entry_price = float(entry_candle["close"])
                exit_price = float(exit_candle["close"])

                exposure = self._current_symbol_exposure(
                    positions,
                    symbol,
                    capital,
                )

                if exposure >= self.max_symbol_exposure_pct:
                    continue

                quantity = self._calculate_position_size(
                    capital,
                    signal.confidence,
                    entry_price,
                )

                if quantity <= 0:
                    continue

                position = Position(
                    strategy_id=strategy.strategy_id,
                    symbol=symbol,
                    side=signal.side,
                    quantity=quantity,
                    entry_price=entry_price,
                    entry_timestamp=timestamp,
                    confidence=signal.confidence,
                )

                positions.append(position)

                slippage_multiplier = 1 + (
                    self.slippage_bps / 10000.0
                )

                effective_entry = entry_price * slippage_multiplier
                effective_exit = exit_price

                if signal.side == "buy":
                    gross_pnl = (
                        effective_exit - effective_entry
                    ) * quantity
                else:
                    gross_pnl = (
                        effective_entry - effective_exit
                    ) * quantity

                fees = (
                    effective_entry
                    * quantity
                    * (self.fee_bps / 10000.0)
                )

                net_pnl = gross_pnl - fees

                capital += net_pnl
                peak_equity = max(peak_equity, capital)

                equity_curve.append(capital)

                trades.append(
                    PortfolioTrade(
                        strategy_id=strategy.strategy_id,
                        symbol=symbol,
                        entry_timestamp=timestamp,
                        exit_timestamp=str(exit_candle["timestamp"]),
                        side=signal.side,
                        quantity=round(quantity, 6),
                        entry_price=round(effective_entry, 4),
                        exit_price=round(effective_exit, 4),
                        gross_pnl=round(gross_pnl, 4),
                        net_pnl=round(net_pnl, 4),
                        fees=round(fees, 4),
                        slippage_bps=self.slippage_bps,
                    )
                )

                symbol_exposure[symbol] = round(
                    self._current_symbol_exposure(
                        positions,
                        symbol,
                        capital,
                    ),
                    4,
                )

                positions.remove(position)

        returns = pd.Series(equity_curve).pct_change().dropna()

        sharpe_ratio = (
            (returns.mean() / returns.std()) * (252**0.5)
            if not returns.empty and returns.std() > 0
            else 0.0
        )

        max_drawdown_pct = (
            (min(equity_curve) - peak_equity)
            / peak_equity
        ) * 100.0

        winning_trades = len(
            [trade for trade in trades if trade.net_pnl > 0]
        )

        losing_trades = len(
            [trade for trade in trades if trade.net_pnl <= 0]
        )

        total_return_pct = (
            (capital - self.initial_capital)
            / self.initial_capital
        ) * 100.0

        return PortfolioBacktestResult(
            initial_capital=self.initial_capital,
            ending_capital=round(capital, 4),
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=round(max_drawdown_pct, 4),
            sharpe_ratio=round(float(sharpe_ratio), 4),
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            active_strategies=[
                strategy.strategy_id
                for strategy in strategies
            ],
            symbol_exposure=symbol_exposure,
            equity_curve=[round(value, 4) for value in equity_curve],
            trades=trades,
            metadata={
                "timeframe": timeframe,
                "max_positions": self.max_positions,
                "risk_per_trade_pct": self.risk_per_trade_pct,
                "fee_bps": self.fee_bps,
                "slippage_bps": self.slippage_bps,
            },
        )
