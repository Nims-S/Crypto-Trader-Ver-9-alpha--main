from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import Signal, Strategy


@dataclass(slots=True)
class LorentzianConfig:
    neighbors_count: int = 8
    lookback_window: int = 2000
    future_bars: int = 4
    use_ema_filter: bool = True
    ema_period: int = 200


class LorentzianClassificationStrategy(Strategy):
    """
    Production-oriented Lorentzian nearest-neighbor classifier.

    Adapted from user-provided research prototype.

    IMPORTANT:
    - This is NOT validated alpha.
    - This is a research candidate only.
    - Requires proper walk-forward and out-of-sample testing.
    """

    def __init__(
        self,
        *,
        strategy_id: str = "lorentzian_v1",
        config: LorentzianConfig | None = None,
    ) -> None:
        self.strategy_id = strategy_id
        self.family = "ml_pattern_matching"
        self.config = config or LorentzianConfig()

    def _calculate_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        high = frame["high"]
        low = frame["low"]
        close = frame["close"]

        features = pd.DataFrame(index=frame.index)

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        rs = (
            gain.rolling(14, min_periods=1).mean()
            / (loss.rolling(14, min_periods=1).mean() + 1e-8)
        )

        features["rsi"] = 100.0 - (100.0 / (1.0 + rs))

        typical_price = (high + low + close) / 3.0

        sma_tp = typical_price.rolling(20, min_periods=1).mean()
        std_tp = typical_price.rolling(20, min_periods=1).std()

        features["cci"] = (
            (typical_price - sma_tp)
            / (0.015 * std_tp + 1e-8)
        )

        features["roc"] = (
            (close - close.shift(14))
            / (close.shift(14) + 1e-8)
        )

        features["ema"] = close.ewm(
            span=self.config.ema_period,
            adjust=False,
        ).mean()

        return features

    def _normalize_features(
        self,
        features: pd.DataFrame,
        columns: list[str],
    ) -> np.ndarray:
        rolling_min = (
            features[columns]
            .rolling(self.config.lookback_window, min_periods=1)
            .min()
        )

        rolling_max = (
            features[columns]
            .rolling(self.config.lookback_window, min_periods=1)
            .max()
        )

        normalized = (
            (features[columns] - rolling_min)
            / (rolling_max - rolling_min + 1e-8)
        )

        return normalized.to_numpy(dtype=np.float64)

    def generate_signals(
        self,
        frame: pd.DataFrame,
    ) -> list[Signal]:
        if len(frame) < self.config.lookback_window:
            return []

        working = frame.copy()
        close = working["close"].to_numpy(dtype=np.float64)

        feature_frame = self._calculate_features(working)

        feature_columns = ["rsi", "cci", "roc"]

        feature_matrix = self._normalize_features(
            feature_frame,
            feature_columns,
        )

        ema_array = feature_frame["ema"].to_numpy(dtype=np.float64)

        n_rows = len(working)

        targets = np.zeros(n_rows, dtype=np.float64)

        future = self.config.future_bars

        targets[:-future] = np.where(
            close[future:] > close[:-future],
            1.0,
            -1.0,
        )

        signals: list[Signal] = []

        start_idx = (
            self.config.lookback_window
            + self.config.future_bars
        )

        for i in range(start_idx, n_rows):
            current_features = feature_matrix[i]

            if np.isnan(current_features).any():
                continue

            start_j = max(0, i - self.config.lookback_window)
            end_j = i - self.config.future_bars

            if start_j >= end_j:
                continue

            historical_features = feature_matrix[start_j:end_j]
            historical_targets = targets[start_j:end_j]

            abs_diff = np.abs(current_features - historical_features)

            distances = np.sum(np.log1p(abs_diff), axis=1)

            k_nearest = min(
                self.config.neighbors_count,
                len(distances) - 1,
            )

            if k_nearest <= 0:
                continue

            nearest_indices = np.argpartition(
                distances,
                k_nearest,
            )[:k_nearest]

            prediction = np.sum(historical_targets[nearest_indices])

            above_ema = (
                close[i] > ema_array[i]
                if self.config.use_ema_filter
                else True
            )

            below_ema = (
                close[i] < ema_array[i]
                if self.config.use_ema_filter
                else True
            )

            if prediction > 0 and above_ema:
                signals.append(
                    Signal(
                        timestamp=str(working.iloc[i]["timestamp"]),
                        symbol="UNKNOWN",
                        side="buy",
                        confidence=min(1.0, abs(prediction) / self.config.neighbors_count),
                        metadata={
                            "prediction": float(prediction),
                            "neighbors": self.config.neighbors_count,
                            "model": "lorentzian_classifier",
                        },
                    )
                )

            elif prediction < 0 and below_ema:
                signals.append(
                    Signal(
                        timestamp=str(working.iloc[i]["timestamp"]),
                        symbol="UNKNOWN",
                        side="sell",
                        confidence=min(1.0, abs(prediction) / self.config.neighbors_count),
                        metadata={
                            "prediction": float(prediction),
                            "neighbors": self.config.neighbors_count,
                            "model": "lorentzian_classifier",
                        },
                    )
                )

        return signals
