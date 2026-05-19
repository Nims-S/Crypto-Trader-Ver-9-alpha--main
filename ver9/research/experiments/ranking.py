from __future__ import annotations

from dataclasses import dataclass

from .tracker import ExperimentRecord


@dataclass(slots=True)
class RankedExperiment:
    experiment_id: str
    strategy_id: str
    composite_score: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    trade_count: int


class ExperimentRanker:
    def rank(
        self,
        records: list[ExperimentRecord],
    ) -> list[RankedExperiment]:
        ranked: list[RankedExperiment] = []

        for record in records:
            metrics = record.metrics

            total_return = float(
                metrics.get("total_return_pct", 0.0)
            )

            sharpe_ratio = float(
                metrics.get("sharpe_ratio", 0.0)
            )

            max_drawdown = abs(
                float(metrics.get("max_drawdown_pct", 0.0))
            )

            trade_count = int(
                metrics.get("trade_count", 0)
            )

            trade_quality = min(1.0, trade_count / 100.0)

            composite_score = (
                (total_return * 0.35)
                + (sharpe_ratio * 35.0)
                - (max_drawdown * 0.45)
                + (trade_quality * 15.0)
            )

            ranked.append(
                RankedExperiment(
                    experiment_id=record.experiment_id,
                    strategy_id=record.strategy_id,
                    composite_score=round(composite_score, 4),
                    total_return_pct=round(total_return, 4),
                    sharpe_ratio=round(sharpe_ratio, 4),
                    max_drawdown_pct=round(max_drawdown, 4),
                    trade_count=trade_count,
                )
            )

        ranked.sort(
            key=lambda item: item.composite_score,
            reverse=True,
        )

        return ranked
