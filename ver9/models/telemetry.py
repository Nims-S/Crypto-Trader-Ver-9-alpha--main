from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RuntimeTelemetry:
    cycle_id: str

    fill_rate: float

    average_slippage_bps: float

    rejection_rate: float

    execution_quality_score: float

    selected_source: str
    selected_source_count: int

    thin_basket_note: str | None

    timestamp: datetime

    metadata: dict[str, Any] = field(default_factory=dict)
