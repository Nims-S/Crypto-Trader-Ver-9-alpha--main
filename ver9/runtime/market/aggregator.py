from __future__ import annotations

from datetime import UTC
from datetime import datetime

from .candles import Candle
from .ticks import Tick


class CandleAggregator:
    """
    Incremental candle aggregation.

    Purpose:
    - aggregate streaming ticks
    - maintain runtime candle state
    - support event-driven signal generation
    - enable incremental market updates
    """

    def __init__(self) -> None:
        self.active_candles: dict[str, Candle] = {}

    def update(
        self,
        *,
        tick: Tick,
        timeframe: str,
    ) -> Candle:
        key = f"{tick.symbol}:{timeframe}"

        existing = self.active_candles.get(key)

        if existing is None:
            candle = Candle(
                symbol=tick.symbol,
                timeframe=timeframe,
                open_price=tick.price,
                high_price=tick.price,
                low_price=tick.price,
                close_price=tick.price,
                volume=tick.volume,
                opened_at=datetime.now(UTC).isoformat(),
            )

            self.active_candles[key] = candle

            return candle

        existing.high_price = max(
            existing.high_price,
            tick.price,
        )

        existing.low_price = min(
            existing.low_price,
            tick.price,
        )

        existing.close_price = tick.price
        existing.volume += tick.volume

        return existing
