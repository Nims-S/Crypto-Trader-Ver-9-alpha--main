from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class MonteCarloPath:
    path_id: int
    ending_equity: float
    max_drawdown_pct: float
    return_pct: float


@dataclass(slots=True)
class MonteCarloResult:
    simulations: int
    median_return_pct: float
    worst_return_pct: float
    best_return_pct: float
    median_drawdown_pct: float
    ruin_probability: float
    paths: list[MonteCarloPath] = field(default_factory=list)


class MonteCarloValidator:
    """
    Equity curve perturbation validator.

    Purpose:
    - estimate path dependency risk
    - estimate ruin probability
    - stress-test strategy robustness
    - expose fragile equity profiles
    """

    def __init__(
        self,
        *,
        simulations: int = 500,
        ruin_threshold_pct: float = -50.0,
        seed: int = 42,
    ) -> None:
        self.simulations = simulations
        self.ruin_threshold_pct = ruin_threshold_pct
        self.random = random.Random(seed)

    def _max_drawdown(
        self,
        equity_curve: list[float],
    ) -> float:
        peak = equity_curve[0]
        max_drawdown = 0.0

        for equity in equity_curve:
            peak = max(peak, equity)

            drawdown = (
                (equity - peak)
                / peak
            ) * 100.0

            max_drawdown = min(max_drawdown, drawdown)

        return abs(max_drawdown)

    def validate(
        self,
        *,
        returns: list[float],
        initial_capital: float = 10000.0,
    ) -> MonteCarloResult:
        if not returns:
            return MonteCarloResult(
                simulations=0,
                median_return_pct=0.0,
                worst_return_pct=0.0,
                best_return_pct=0.0,
                median_drawdown_pct=0.0,
                ruin_probability=1.0,
            )

        paths: list[MonteCarloPath] = []

        ruined = 0

        for path_id in range(self.simulations):
            shuffled = returns.copy()
            self.random.shuffle(shuffled)

            equity = initial_capital
            equity_curve = [equity]

            for trade_return in shuffled:
                equity *= (1.0 + trade_return)
                equity_curve.append(equity)

            return_pct = (
                (equity - initial_capital)
                / initial_capital
            ) * 100.0

            drawdown = self._max_drawdown(equity_curve)

            if return_pct <= self.ruin_threshold_pct:
                ruined += 1

            paths.append(
                MonteCarloPath(
                    path_id=path_id,
                    ending_equity=round(equity, 4),
                    max_drawdown_pct=round(drawdown, 4),
                    return_pct=round(return_pct, 4),
                )
            )

        return_values = [path.return_pct for path in paths]
        drawdown_values = [
            path.max_drawdown_pct
            for path in paths
        ]

        return MonteCarloResult(
            simulations=self.simulations,
            median_return_pct=round(
                float(np.median(return_values)),
                4,
            ),
            worst_return_pct=round(
                float(min(return_values)),
                4,
            ),
            best_return_pct=round(
                float(max(return_values)),
                4,
            ),
            median_drawdown_pct=round(
                float(np.median(drawdown_values)),
                4,
            ),
            ruin_probability=round(
                ruined / self.simulations,
                4,
            ),
            paths=paths,
        )
