from __future__ import annotations

import pandas as pd

from .base import Signal, Strategy


class SmaCrossStrategy(Strategy):
    def __init__(
        self,
        *,
        strategy_id: str = "sma_cross_v1",
        fast_period: int = 20,
        slow_period: int = 50,
    ) -> None:
        self.strategy_id = strategy_id
        self.family = "trend_following"
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(
        self,
        frame: pd.DataFrame,
    ) -> list[Signal]:
        if len(frame) < self.slow_period:
            return []

        working = frame.copy()

        working["fast_sma"] = (
            working["close"]
            .rolling(self.fast_period, min_periods=self.fast_period)
            .mean()
        )

        working["slow_sma"] = (
            working["close"]
            .rolling(self.slow_period, min_periods=self.slow_period)
            .mean()
        )

        working["cross_up"] = (
            (working["fast_sma"] > working["slow_sma"])
            & (working["fast_sma"].shift(1) <= working["slow_sma"].shift(1))
        )

        signals: list[Signal] = []

        for row in working.loc[working["cross_up"]].itertuples():
            signals.append(
                Signal(
                    timestamp=str(row.timestamp),
                    symbol="UNKNOWN",
                    side="buy",
                    confidence=0.55,
                    metadata={
                        "fast_sma": round(float(row.fast_sma), 4),
                        "slow_sma": round(float(row.slow_sma), 4),
                    },
                )
            )

        return signals
