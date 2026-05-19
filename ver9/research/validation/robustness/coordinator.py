from __future__ import annotations

from dataclasses import dataclass

from ...optimization.search import OptimizationCandidate
from .monte_carlo import MonteCarloResult, MonteCarloValidator
from .stability import ParameterStabilityValidator, StabilityResult


@dataclass(slots=True)
class ValidationSummary:
    monte_carlo: MonteCarloResult
    parameter_stability: StabilityResult
    overall_pass: bool
    summary_score: float


class RobustnessCoordinator:
    def __init__(
        self,
        *,
        monte_carlo_validator: MonteCarloValidator | None = None,
        stability_validator: ParameterStabilityValidator | None = None,
    ) -> None:
        self.monte_carlo_validator = (
            monte_carlo_validator or MonteCarloValidator()
        )

        self.stability_validator = (
            stability_validator or ParameterStabilityValidator()
        )

    def evaluate(
        self,
        *,
        trade_returns: list[float],
        optimization_candidates: list[OptimizationCandidate],
        initial_capital: float = 10000.0,
    ) -> ValidationSummary:
        monte_carlo_result = self.monte_carlo_validator.validate(
            returns=trade_returns,
            initial_capital=initial_capital,
        )

        stability_result = self.stability_validator.validate(
            optimization_candidates
        )

        score = 100.0

        score -= (
            monte_carlo_result.ruin_probability * 100.0
        )

        score -= (
            stability_result.variability_ratio * 50.0
        )

        if not stability_result.stable:
            score -= 15.0

        score = max(0.0, score)

        overall_pass = (
            monte_carlo_result.ruin_probability < 0.25
            and stability_result.stable
            and score >= 50.0
        )

        return ValidationSummary(
            monte_carlo=monte_carlo_result,
            parameter_stability=stability_result,
            overall_pass=overall_pass,
            summary_score=round(score, 4),
        )
