from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean

from .state_models import RuntimeSnapshot
from .state_models import SystemStatus


@dataclass(slots=True)
class SupervisionState:
    runtime_id: str
    status: str
    average_latency_ms: float
    escalation_level: int
    coordination_active: bool
    updated_at: str


class RuntimeSupervisionLayer:
    def __init__(
        self,
        *,
        warning_latency_ms: float = 750.0,
        critical_latency_ms: float = 2000.0,
    ) -> None:
        self.warning_latency_ms = warning_latency_ms
        self.critical_latency_ms = critical_latency_ms

        self.latency_history: list[float] = []

    def supervise(
        self,
        *,
        snapshot: RuntimeSnapshot,
        latency_ms: float,
    ) -> SupervisionState:
        self.latency_history.append(latency_ms)

        rolling_latency = mean(self.latency_history[-25:])

        escalation_level = 0

        if rolling_latency >= self.critical_latency_ms:
            snapshot.system_status = SystemStatus.HALTED.value
            escalation_level = 2

        elif rolling_latency >= self.warning_latency_ms:
            snapshot.system_status = SystemStatus.WARNING.value
            escalation_level = 1

        else:
            snapshot.system_status = SystemStatus.ACTIVE.value

        snapshot.refresh()

        return SupervisionState(
            runtime_id=snapshot.runtime_id,
            status=snapshot.system_status,
            average_latency_ms=round(rolling_latency, 4),
            escalation_level=escalation_level,
            coordination_active=snapshot.system_status
            != SystemStatus.HALTED.value,
            updated_at=datetime.now(UTC).isoformat(),
        )
