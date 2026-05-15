from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StrategyEvidence:
    monte_carlo_score: float = 0.0
    perturbation_score: float = 0.0
    walk_forward_score: float = 0.0
    cross_symbol_score: float = 0.0
    robustness_score: float = 0.0


@dataclass(slots=True)
class StrategyCandidate:
    strategy_id: str
    symbol: str
    timeframe: str
    regime: str
    family: str
    profit_factor: float
    return_pct: float
    max_drawdown_pct: float
    trades: int
    evidence: StrategyEvidence = field(default_factory=StrategyEvidence)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MarketProfile:
    symbol: str
    spread_bps: float
    volume_score: float
    volatility_score: float
    health_score: float
    tradable: bool = True


@dataclass(slots=True)
class ProtectionDecision:
    approved: bool
    reason: str
    cooldown_minutes: int = 0
    capital_multiplier: float = 1.0


@dataclass(slots=True)
class PortfolioAllocation:
    strategy_id: str
    symbol: str
    allocation_pct: float
    probationary: bool
    expected_risk: float


@dataclass(slots=True)
class ArtifactRecord:
    cycle_id: str
    generated_at: str
    config: dict[str, Any]
    survivors: list[dict[str, Any]]
    portfolio: list[dict[str, Any]]
    protections: list[dict[str, Any]]
