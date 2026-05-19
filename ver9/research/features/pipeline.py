from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class FeaturePipelineResult:
    frame: pd.DataFrame
    feature_columns: list[str]
    dropped_rows: int


class FeaturePipeline:
    """
    Centralized feature computation pipeline.

    Purpose:
    - standardize feature generation
    - reduce duplicated indicator logic
    - reduce feature leakage risk
    - establish reproducible feature lineage
    """

    def __init__(
        self,
        *,
        rsi_period: int = 14,
        roc_period: int = 14,
        ema_fast: int = 50,
        ema_slow: int = 200,
        volatility_window: int = 50,
    ) -> None:
        self.rsi_period = rsi_period
        self.roc_period = roc_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volatility_window = volatility_window

    def _compute_rsi(
        self,
        close: pd.Series,
    ) -> pd.Series:
        delta = close.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(
            self.rsi_period,
            min_periods=self.rsi_period,
        ).mean()

        avg_loss = loss.rolling(
            self.rsi_period,
            min_periods=self.rsi_period,
        ).mean()

        rs = avg_gain / (avg_loss + 1e-8)

        return 100.0 - (100.0 / (1.0 + rs))

    def _compute_cci(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
    ) -> pd.Series:
        typical_price = (high + low + close) / 3.0

        sma_tp = typical_price.rolling(20).mean()
        mad = (
            typical_price
            .rolling(20)
            .apply(
                lambda values: np.mean(
                    np.abs(values - np.mean(values))
                ),
                raw=True,
            )
        )

        return (
            (typical_price - sma_tp)
            / (0.015 * mad + 1e-8)
        )

    def _compute_roc(
        self,
        close: pd.Series,
    ) -> pd.Series:
        return (
            (close - close.shift(self.roc_period))
            / (close.shift(self.roc_period) + 1e-8)
        )

    def _compute_realized_volatility(
        self,
        close: pd.Series,
    ) -> pd.Series:
        returns = np.log(
            close / close.shift(1)
        )

        return returns.rolling(
            self.volatility_window
        ).std()

    def build(
        self,
        frame: pd.DataFrame,
    ) -> FeaturePipelineResult:
        working = frame.copy()

        working["rsi"] = self._compute_rsi(
            working["close"]
        )

        working["cci"] = self._compute_cci(
            working["high"],
            working["low"],
            working["close"],
        )

        working["roc"] = self._compute_roc(
            working["close"]
        )

        working["ema_fast"] = working["close"].ewm(
            span=self.ema_fast,
            adjust=False,
        ).mean()

        working["ema_slow"] = working["close"].ewm(
            span=self.ema_slow,
            adjust=False,
        ).mean()

        working["realized_volatility"] = (
            self._compute_realized_volatility(
                working["close"]
            )
        )

        working["volume_zscore"] = (
            (working["volume"] - working["volume"].rolling(50).mean())
            / (
                working["volume"].rolling(50).std()
                + 1e-8
            )
        )

        feature_columns = [
            "rsi",
            "cci",
            "roc",
            "ema_fast",
            "ema_slow",
            "realized_volatility",
            "volume_zscore",
        ]

        initial_rows = len(working)

        working = working.dropna().reset_index(drop=True)

        dropped_rows = initial_rows - len(working)

        return FeaturePipelineResult(
            frame=working,
            feature_columns=feature_columns,
            dropped_rows=dropped_rows,
        )
