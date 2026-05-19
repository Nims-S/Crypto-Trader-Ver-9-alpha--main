from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ...optimization.search import OptimizationCandidate


@dataclass(slots=True)
class StabilityWindow:
    window_id: int
    score_mean: float
    score_std: float
    variability_ratio: float


@dataclass(slots=True)
class StabilityResult:
    stable: bool
    mean_score: float
    score_std: float
    variability_ratio: float
    windows: list[StabilityWindow] = field(default_factory=list)


class ParameterStabilityValidator:
    def __init__(
        self,
        *,
        variability_threshold: float = 0.35,
    ) -> None:
        self.variability_threshold = variability_threshold

    def validate(
        self,
        candidates: list[OptimizationCandidate],
    ) -> StabilityResult:
        if not candidates:
            return StabilityResult(
                stable=False,
                mean_score=0.0,
                score_std=0.0,
                variability_ratio=1.0,
            )

        scores = np.array(
            [candidate.composite_score for candidate in candidates]
        )

        score_mean = float(np.mean(scores))
        score_std = float(np.std(scores))

        variability_ratio = (
            score_std / (abs(score_mean) + 1e-8)
        )

        windows: list[StabilityWindow] = []

        chunk_size = max(1, len(scores) // 5)

        for idx in range(0, len(scores), chunk_size):
            chunk = scores[idx : idx + chunk_size]

            if len(chunk) == 0:
                continue

            chunk_mean = float(np.mean(chunk))
            chunk_std = float(np.std(chunk))

            chunk_ratio = (
                chunk_std / (abs(chunk_mean) + 1e-8)
            )

            windows.append(
                StabilityWindow(
                    window_id=len(windows),
                    score_mean=round(chunk_mean, 4),
                    score_std=round(chunk_std, 4),
                    variability_ratio=round(chunk_ratio, 4),
                )
            )

        return StabilityResult(
            stable=variability_ratio < self.variability_threshold,
            mean_score=round(score_mean, 4),
            score_std=round(score_std, 4),
            variability_ratio=round(variability_ratio, 4),
            windows=windows,
        )
