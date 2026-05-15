from __future__ import annotations

from dataclasses import asdict

from .models import MarketProfile


class PairUniverseManager:
    def __init__(
        self,
        *,
        max_spread_bps: float = 12.0,
        min_volume_score: float = 0.45,
        min_health_score: float = 0.55,
    ) -> None:
        self.max_spread_bps = max_spread_bps
        self.min_volume_score = min_volume_score
        self.min_health_score = min_health_score

    def evaluate(self, profiles: list[MarketProfile]) -> list[dict]:
        approved: list[dict] = []
        for profile in profiles:
            if not profile.tradable:
                continue
            if profile.spread_bps > self.max_spread_bps:
                continue
            if profile.volume_score < self.min_volume_score:
                continue
            if profile.health_score < self.min_health_score:
                continue
            approved.append(asdict(profile))
        return approved


DEFAULT_UNIVERSE = [
    MarketProfile(
        symbol="BTC/USDT",
        spread_bps=2.0,
        volume_score=0.98,
        volatility_score=0.72,
        health_score=0.96,
    ),
    MarketProfile(
        symbol="ETH/USDT",
        spread_bps=3.0,
        volume_score=0.91,
        volatility_score=0.75,
        health_score=0.91,
    ),
    MarketProfile(
        symbol="SOL/USDT",
        spread_bps=6.0,
        volume_score=0.74,
        volatility_score=0.88,
        health_score=0.79,
    ),
]
