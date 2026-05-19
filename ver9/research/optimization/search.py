from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..backtesting.portfolio_engine import PortfolioBacktestEngine
from ..experiments.tracker import ExperimentTracker
from ..strategies.base import Strategy


@dataclass(slots=True)
class OptimizationCandidate:
    parameters: dict[str, Any]
    metrics: dict[str, float]
    composite_score: float


@dataclass(slots=True)
class OptimizationResult:
    strategy_id: str
    total_candidates: int
    best_candidate: OptimizationCandidate
    ranked_candidates: list[OptimizationCandidate] = field(
        default_factory=list
    )


class GridSearchOptimizer:
    """
    Controlled parameter optimization.

    Goals:
    - reproducible parameter sweeps
    - bounded search spaces
    - walk-forward compatible evaluation
    - experiment traceability
    - anti-chaotic manual tuning
    """

    def __init__(
        self,
        *,
        tracker: ExperimentTracker | None = None,
    ) -> None:
        self.tracker = tracker

    def _parameter_combinations(
        self,
        parameter_space: dict[str, list[Any]],
    ) -> list[dict[str, Any]]:
        keys = list(parameter_space.keys())
        values = [parameter_space[key] for key in keys]

        combinations = []

        for combo in itertools.product(*values):
            combinations.append(
                {
                    key: value
                    for key, value in zip(keys, combo)
                }
            )

        return combinations

    def _score(
        self,
        metrics: dict[str, float],
    ) -> float:
        total_return = metrics.get(
            "total_return_pct",
            0.0,
        )

        sharpe = metrics.get(
            "sharpe_ratio",
            0.0,
        )

        drawdown = abs(
            metrics.get(
                "max_drawdown_pct",
                0.0,
            )
        )

        trade_count = metrics.get(
            "trade_count",
            0.0,
        )

        trade_quality = min(1.0, trade_count / 100.0)

        return (
            (total_return * 0.35)
            + (sharpe * 35.0)
            - (drawdown * 0.45)
            + (trade_quality * 15.0)
        )

    def optimize(
        self,
        *,
        strategy_factory: type[Strategy],
        parameter_space: dict[str, list[Any]],
        frame: pd.DataFrame,
        symbol: str,
        timeframe: str,
        initial_capital: float = 10000.0,
    ) -> OptimizationResult:
        combinations = self._parameter_combinations(
            parameter_space
        )

        ranked: list[OptimizationCandidate] = []

        for parameters in combinations:
            strategy = strategy_factory(**parameters)

            engine = PortfolioBacktestEngine(
                initial_capital=initial_capital,
            )

            result = engine.run(
                strategies=[strategy],
                frame=frame,
                symbol=symbol,
                timeframe=timeframe,
            )

            metrics = {
                "total_return_pct": result.total_return_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
                "trade_count": result.total_trades,
            }

            composite_score = self._score(metrics)

            candidate = OptimizationCandidate(
                parameters=parameters,
                metrics=metrics,
                composite_score=round(composite_score, 4),
            )

            ranked.append(candidate)

            if self.tracker:
                record = self.tracker.create_experiment(
                    strategy_id=strategy.strategy_id,
                    strategy_family=getattr(
                        strategy,
                        "family",
                        "unknown",
                    ),
                    symbol=symbol,
                    timeframe=timeframe,
                    dataset_rows=len(frame),
                    parameters=parameters,
                    metrics=metrics,
                    walkforward_summary={},
                    tags=["optimization", "grid_search"],
                    notes="parameter optimization run",
                )

                self.tracker.save(record)

        ranked.sort(
            key=lambda item: item.composite_score,
            reverse=True,
        )

        return OptimizationResult(
            strategy_id=ranked[0].parameters.__class__.__name__
            if ranked
            else "unknown",
            total_candidates=len(ranked),
            best_candidate=ranked[0],
            ranked_candidates=ranked,
        )
