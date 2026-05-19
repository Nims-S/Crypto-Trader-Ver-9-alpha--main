from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..backtesting.engine import BacktestEngine, BacktestResult
from ..strategies.base import Strategy


@dataclass(slots=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(slots=True)
class WalkForwardResult:
    windows: list[WalkForwardWindow]
    test_results: list[BacktestResult]


class WalkForwardValidator:
    def __init__(
        self,
        *,
        train_size: int = 500,
        test_size: int = 100,
        step_size: int = 100,
    ) -> None:
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size

    def validate(
        self,
        *,
        strategy: Strategy,
        frame: pd.DataFrame,
        symbol: str,
        timeframe: str,
        engine: BacktestEngine,
    ) -> WalkForwardResult:
        windows: list[WalkForwardWindow] = []
        results: list[BacktestResult] = []

        cursor = self.train_size

        while cursor + self.test_size <= len(frame):
            train_start = cursor - self.train_size
            train_end = cursor
            test_start = cursor
            test_end = cursor + self.test_size

            window = WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )

            test_frame = frame.iloc[test_start:test_end].copy()

            result = engine.run(
                strategy=strategy,
                frame=test_frame,
                symbol=symbol,
                timeframe=timeframe,
            )

            windows.append(window)
            results.append(result)

            cursor += self.step_size

        return WalkForwardResult(
            windows=windows,
            test_results=results,
        )
