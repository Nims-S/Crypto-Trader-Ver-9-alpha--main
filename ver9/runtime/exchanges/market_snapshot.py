from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class VenueMarketSnapshot:
    venue: str
    symbol: str
    bid_price: float
    ask_price: float
    last_price: float
    volume: float
    updated_at: str
    metadata: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        venue: str,
        symbol: str,
        bid_price: float,
        ask_price: float,
        last_price: float,
        volume: float,
        metadata: dict[str, Any] | None = None,
    ) -> "VenueMarketSnapshot":
        return cls(
            venue=venue,
            symbol=symbol,
            bid_price=bid_price,
            ask_price=ask_price,
            last_price=last_price,
            volume=volume,
            updated_at=datetime.now(UTC).isoformat(),
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
