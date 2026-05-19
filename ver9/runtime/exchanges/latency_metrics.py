from dataclasses import dataclass
from statistics import mean


@dataclass(slots=True)
class LatencyMetrics:
    average_latency_ms: float
    maximum_latency_ms: float
    sample_count: int


class LatencyMetricTracker:
    def __init__(self) -> None:
        self.samples: list[float] = []

    def add_sample(
        self,
        latency_ms: float,
    ) -> LatencyMetrics:
        self.samples.append(latency_ms)

        return LatencyMetrics(
            average_latency_ms=round(
                mean(self.samples),
                4,
            ),
            maximum_latency_ms=round(
                max(self.samples),
                4,
            ),
            sample_count=len(self.samples),
        )
