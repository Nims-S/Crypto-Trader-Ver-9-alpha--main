from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AllocationDecision:
    strategy_id: str

    symbol: str

    weight: float
    capital_allocated: float

    expected_risk: float
    covariance_penalty: float

    selection_reason: str

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PortfolioSnapshot:
    total_capital: float

    gross_exposure: float
    net_exposure: float

    cash_weight: float

    allocations: list[AllocationDecision]
