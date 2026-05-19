from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ExecutionResult:
    strategy_id: str

    symbol: str
    side: str

    requested_qty: float
    filled_qty: float

    requested_price: float
    average_fill_price: float

    slippage_bps: float

    latency_ms: int

    status: str

    rejection_reason: str | None

    timestamp: datetime
