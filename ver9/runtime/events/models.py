from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"
    POSITION = "position"
    RISK = "risk"
    RUNTIME = "runtime"


@dataclass(slots=True)
class RuntimeEvent:
    event_id: str
    event_type: str
    source: str
    created_at: str
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        event_type: str,
        source: str,
        payload: dict[str, Any],
    ) -> "RuntimeEvent":
        return cls(
            event_id=event_id,
            event_type=event_type,
            source=source,
            created_at=datetime.now(UTC).isoformat(),
            payload=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
