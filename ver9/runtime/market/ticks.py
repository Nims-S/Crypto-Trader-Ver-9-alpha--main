from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(slots=True)
class Tick:
    symbol: str
    price: float
    volume: float
    timestamp: str

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        price: float,
        volume: float,
    ) -> "Tick":
        return cls(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=datetime.now(UTC).isoformat(),
        )
