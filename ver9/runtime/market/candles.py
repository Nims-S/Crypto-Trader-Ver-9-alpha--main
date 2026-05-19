from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Candle:
    symbol: str
    timeframe: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    opened_at: str
    closed_at: str | None = None
