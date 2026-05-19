from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from time import time


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(slots=True)
class ExecutionOrder:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None = None

    client_order_id: str = field(
        default_factory=lambda: f"ver9-{uuid.uuid4().hex[:16]}"
    )

    exchange_order_id: str | None = None
    status: OrderStatus = OrderStatus.CREATED

    filled_quantity: float = 0.0
    average_fill_price: float = 0.0

    retry_count: int = 0

    created_ts: float = field(default_factory=time)
    updated_ts: float = field(default_factory=time)

    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)
