from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    last_price: float
    last_volume: float
    updated_at: str

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        last_price: float,
        last_volume: float,
    ) -> "MarketSnapshot":
        return cls(
            symbol=symbol,
            last_price=last_price,
            last_volume=last_volume,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class MarketSnapshotStore:
    def __init__(self) -> None:
        self.snapshots: dict[str, MarketSnapshot] = {}

    def update(
        self,
        snapshot: MarketSnapshot,
    ) -> None:
        self.snapshots[snapshot.symbol] = snapshot

    def get(
        self,
        symbol: str,
    ) -> MarketSnapshot | None:
        return self.snapshots.get(symbol)
