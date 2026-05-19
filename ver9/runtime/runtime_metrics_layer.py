from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(slots=True)
class RuntimeMetricSnapshot:
    latency_ms: float
    rolling_latency_ms: float
    sample_count: int


@dataclass(slots=True)
class RuntimeMetricSummary:
    average_latency_ms: float
    highest_latency_ms: float
    total_samples: int


class RuntimeMetricsLayer:
    def __init__(
        self,
        *,
        rolling_window: int = 25,
    ) -> None:
        self.rolling_window = rolling_window
        self.samples: list[float] = []

    def add_sample(
        self,
        latency_ms: float,
    ) -> RuntimeMetricSnapshot:
        self.samples.append(latency_ms)

        rolling = self.samples[-self.rolling_window :]

        rolling_latency = mean(rolling)

        return RuntimeMetricSnapshot(
            latency_ms=round(latency_ms, 4),
            rolling_latency_ms=round(rolling_latency, 4),
            sample_count=len(self.samples),
        )

    def summary(self) -> RuntimeMetricSummary:
        if not self.samples:
            return RuntimeMetricSummary(
                average_latency_ms=0.0,
                highest_latency_ms=0.0,
                total_samples=0,
            )

        return RuntimeMetricSummary(
            average_latency_ms=round(
                mean(self.samples),
                4,
            ),
            highest_latency_ms=round(
                max(self.samples),
                4,
            ),
            total_samples=len(self.samples),
        )
