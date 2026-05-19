from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


@dataclass(slots=True)
class MarketDataset:
    symbol: str
    timeframe: str
    frame: pd.DataFrame


class MarketDataError(RuntimeError):
    pass


class MarketDataLoader:
    def __init__(self, root: str = "data") -> None:
        self.root = Path(root)

    def load_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
    ) -> MarketDataset:
        normalized_symbol = symbol.replace("/", "_").lower()

        csv_path = (
            self.root
            / normalized_symbol
            / f"{timeframe}.csv"
        )

        parquet_path = (
            self.root
            / normalized_symbol
            / f"{timeframe}.parquet"
        )

        if parquet_path.exists():
            frame = pd.read_parquet(parquet_path)
        elif csv_path.exists():
            frame = pd.read_csv(csv_path)
        else:
            raise MarketDataError(
                f"missing market data for {symbol} {timeframe}"
            )

        missing = REQUIRED_COLUMNS - set(frame.columns)

        if missing:
            raise MarketDataError(
                f"market data missing columns: {sorted(missing)}"
            )

        frame = frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").reset_index(drop=True)

        return MarketDataset(
            symbol=symbol,
            timeframe=timeframe,
            frame=frame,
        )
