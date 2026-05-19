from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class FillStatus(str, Enum):
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"


@dataclass(slots=True)
class SimulatedOrder:
    strategy_id: str
    symbol: str
    side: str
    order_type: str
    requested_quantity: float
    requested_price: float
    confidence: float
    timestamp: str


@dataclass(slots=True)
class SimulatedFill:
    strategy_id: str
    symbol: str
    side: str
    requested_quantity: float
    filled_quantity: float
    requested_price: float
    executed_price: float
    slippage_pct: float
    fees_paid: float
    latency_ms: int
    status: str
    timestamp: str


@dataclass(slots=True)
class ExecutionMetrics:
    total_orders: int = 0
    filled_orders: int = 0
    rejected_orders: int = 0
    partial_fills: int = 0

    average_slippage_pct: float = 0.0
    average_latency_ms: float = 0.0
    total_fees_paid: float = 0.0

    fill_rate: float = 0.0


@dataclass(slots=True)
class SimulationResult:
    fills: list[SimulatedFill] = field(default_factory=list)
    metrics: ExecutionMetrics = field(
        default_factory=ExecutionMetrics
    )
