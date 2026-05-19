from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(slots=True)
class RuntimeMetrics:
    average_latency_ms: float
    peak_latency_ms: float
    event_count: int
    classification: str


class RuntimeMetricsAnalyzer:
    def __init__(
        self,
        *,
        elevated_threshold_ms: float = 750.0,
        severe_threshold_ms: float = 2000.0,
    ) -> None:
        self.elevated_threshold_ms = elevated_threshold_ms
        self.severe_threshold_ms = severe_threshold_ms

    def classify(
        self,
        latencies: list[float],
    ) -> RuntimeMetrics:
        if not latencies:
            return RuntimeMetrics(
                average_latency_ms=0.0,
                peak_latency_ms=0.0,
                event_count=0,
                classification="idle",
            )

        average_latency = mean(latencies)
        peak_latency = max(latencies)

        if average_latency >= self.severe_threshold_ms:
            classification = "severe"
        elif average_latency >= self.elevated_threshold_ms:
            classification = "elevated"
        else:
            classification = "normal"

        return RuntimeMetrics(
            average_latency_ms=round(average_latency, 4),
            peak_latency_ms=round(peak_latency, 4),
            event_count=len(latencies),
            classification=classification,
        )
