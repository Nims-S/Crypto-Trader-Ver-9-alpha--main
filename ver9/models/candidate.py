from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class StrategyCandidate:
    strategy_id: str
    family: str
    generation: int
    status: str

    symbols: list[str]

    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float

    robustness_score: float
    execution_quality_score: float

    created_at: datetime

    parent_strategy_id: str | None = None
    mutation_type: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
