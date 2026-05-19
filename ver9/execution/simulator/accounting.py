from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PositionSnapshot:
    symbol: str
    quantity: float
    average_price: float


@dataclass(slots=True)
class BalanceSnapshot:
    total_equity: float
    available_cash: float
