from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MarketRegime:
    volatility_regime: str
    trend_regime: str
    liquidity_regime: str
    correlation_regime: str

    confidence: float

    timestamp: datetime
