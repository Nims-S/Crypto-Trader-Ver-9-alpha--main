from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class NormalizedTicker:
    symbol: str
    bid_price: float
    ask_price: float
    last_price: float
    volume: float
    venue: str
    timestamp: str


class TickerNormalizer:
    """
    Normalize heterogeneous exchange ticker payloads.

    Purpose:
    - venue abstraction mapping
    - exchange payload normalization
    - standardized market data formatting
    - runtime interoperability
    """

    def normalize(
        self,
        *,
        venue: str,
        payload: dict[str, Any],
    ) -> NormalizedTicker:
        symbol = self._extract_symbol(payload)

        bid_price = self._to_float(
            payload.get("bid")
            or payload.get("bestBid")
            or payload.get("b")
            or 0.0
        )

        ask_price = self._to_float(
            payload.get("ask")
            or payload.get("bestAsk")
            or payload.get("a")
            or 0.0
        )

        last_price = self._to_float(
            payload.get("last")
            or payload.get("lastPrice")
            or payload.get("c")
            or payload.get("price")
            or 0.0
        )

        volume = self._to_float(
            payload.get("volume")
            or payload.get("baseVolume")
            or payload.get("v")
            or 0.0
        )

        timestamp = (
            payload.get("timestamp")
            or datetime.now(UTC).isoformat()
        )

        return NormalizedTicker(
            symbol=symbol,
            bid_price=bid_price,
            ask_price=ask_price,
            last_price=last_price,
            volume=volume,
            venue=venue,
            timestamp=str(timestamp),
        )

    def _extract_symbol(
        self,
        payload: dict[str, Any],
    ) -> str:
        return str(
            payload.get("symbol")
            or payload.get("s")
            or payload.get("market")
            or "UNKNOWN"
        )

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
