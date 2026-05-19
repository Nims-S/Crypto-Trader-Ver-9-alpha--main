from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class LifecycleTransition:
    strategy_id: str

    from_status: str
    to_status: str

    reason: str

    timestamp: datetime
