from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class VolatilityRegime(str, Enum):
    LOW = "low_volatility"
    NORMAL = "normal_volatility"
    HIGH = "high_volatility"
    EXTREME = "extreme_volatility"


class TrendRegime(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"


class LiquidityRegime(str, Enum):
    LOW = "low_liquidity"
    NORMAL = "normal_liquidity"
    HIGH = "high_liquidity"


@dataclass(slots=True)
class RegimeState:
    timestamp: str

    volatility_regime: str
    trend_regime: str
    liquidity_regime: str

    realized_volatility: float
    trend_strength: float
    volume_zscore: float


class MarketRegimeClassifier:
    def __init__(
        self,
        *,
        volatility_window: int = 50,
        trend_window: int = 200,
        liquidity_window: int = 50,
    ) -> None:
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        self.liquidity_window = liquidity_window

    def _compute_realized_volatility(
        self,
        close: pd.Series,
    ) -> pd.Series:
        log_returns = np.log(
            close / close.shift(1)
        )

        return (
            log_returns
            .rolling(self.volatility_window)
            .std()
            * np.sqrt(252)
        )

    def _compute_trend_strength(
        self,
        close: pd.Series,
    ) -> tuple[pd.Series, pd.Series]:
        fast_ema = close.ewm(
            span=50,
            adjust=False,
        ).mean()

        slow_ema = close.ewm(
            span=self.trend_window,
            adjust=False,
        ).mean()

        trend_strength = (
            (fast_ema - slow_ema)
            / (slow_ema + 1e-8)
        )

        return fast_ema, trend_strength

    def _compute_volume_zscore(
        self,
        volume: pd.Series,
    ) -> pd.Series:
        rolling_mean = volume.rolling(
            self.liquidity_window
        ).mean()

        rolling_std = volume.rolling(
            self.liquidity_window
        ).std()

        return (
            (volume - rolling_mean)
            / (rolling_std + 1e-8)
        )

    def classify(
        self,
        frame: pd.DataFrame,
    ) -> list[RegimeState]:
        if len(frame) < self.trend_window:
            return []

        working = frame.copy()

        close = working["close"]
        volume = working["volume"]

        realized_volatility = (
            self._compute_realized_volatility(close)
        )

        _, trend_strength = self._compute_trend_strength(close)

        volume_zscore = self._compute_volume_zscore(volume)

        volatility_quantiles = realized_volatility.quantile(
            [0.25, 0.75, 0.9]
        )

        regimes: list[RegimeState] = []

        for idx in range(len(working)):
            row = working.iloc[idx]

            volatility_value = float(
                realized_volatility.iloc[idx]
                if not pd.isna(realized_volatility.iloc[idx])
                else 0.0
            )

            trend_value = float(
                trend_strength.iloc[idx]
                if not pd.isna(trend_strength.iloc[idx])
                else 0.0
            )

            volume_value = float(
                volume_zscore.iloc[idx]
                if not pd.isna(volume_zscore.iloc[idx])
                else 0.0
            )

            if volatility_value >= volatility_quantiles.loc[0.9]:
                volatility_regime = VolatilityRegime.EXTREME.value
            elif volatility_value >= volatility_quantiles.loc[0.75]:
                volatility_regime = VolatilityRegime.HIGH.value
            elif volatility_value <= volatility_quantiles.loc[0.25]:
                volatility_regime = VolatilityRegime.LOW.value
            else:
                volatility_regime = VolatilityRegime.NORMAL.value

            if trend_value > 0.015:
                trend_regime = TrendRegime.BULLISH.value
            elif trend_value < -0.015:
                trend_regime = TrendRegime.BEARISH.value
            else:
                trend_regime = TrendRegime.SIDEWAYS.value

            if volume_value > 1.0:
                liquidity_regime = LiquidityRegime.HIGH.value
            elif volume_value < -1.0:
                liquidity_regime = LiquidityRegime.LOW.value
            else:
                liquidity_regime = LiquidityRegime.NORMAL.value

            regimes.append(
                RegimeState(
                    timestamp=str(row["timestamp"]),
                    volatility_regime=volatility_regime,
                    trend_regime=trend_regime,
                    liquidity_regime=liquidity_regime,
                    realized_volatility=round(volatility_value, 6),
                    trend_strength=round(trend_value, 6),
                    volume_zscore=round(volume_value, 6),
                )
            )

        return regimes
