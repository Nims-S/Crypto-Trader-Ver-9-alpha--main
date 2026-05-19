from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Any


class SystemStatus(str, Enum):
    ACTIVE = "active"
    WARNING = "warning"
    HALTED = "halted"


@dataclass(slots=True)
class PositionState:
    symbol: str
    quantity: float
    entry_price: float
    unrealized_pnl: float = 0.0


@dataclass(slots=True)
class HeartbeatState:
    timestamp: str
    latency_ms: float
    active_strategies: int
    open_positions: int
    system_status: str


@dataclass(slots=True)
class RuntimeSnapshot:
    runtime_id: str
    started_at: str
    updated_at: str
    system_status: str
    cash_balance: float
    equity: float
    active_strategy_ids: list[str] = field(default_factory=list)
    positions: list[PositionState] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        runtime_id: str,
        initial_equity: float,
    ) -> "RuntimeSnapshot":
        now = datetime.now(UTC).isoformat()

        return cls(
            runtime_id=runtime_id,
            started_at=now,
            updated_at=now,
            system_status=SystemStatus.ACTIVE.value,
            cash_balance=initial_equity,
            equity=initial_equity,
        )

    def refresh(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
