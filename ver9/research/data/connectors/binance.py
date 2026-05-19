from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ccxt
import pandas as pd


logger = logging.getLogger(__name__)


SUPPORTED_TIMEFRAMES = {
    "1m",
    "5m",
    "15m",
    "1h",
    "4h",
    "1d",
}


@dataclass(slots=True)
class DownloadResult:
    symbol: str
    timeframe: str
    rows_downloaded: int
    output_path: str


class BinanceDataError(RuntimeError):
    pass


class BinanceHistoricalDownloader:
    def __init__(
        self,
        *,
        data_root: str = "data",
        rate_limit: bool = True,
    ) -> None:
        self.data_root = Path(data_root)

        self.exchange = ccxt.binance(
            {
                "enableRateLimit": rate_limit,
            }
        )

    def _validate_timeframe(self, timeframe: str) -> None:
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise BinanceDataError(
                f"unsupported timeframe: {timeframe}"
            )

    def _symbol_directory(self, symbol: str) -> Path:
        normalized = symbol.replace("/", "_").lower()
        path = self.data_root / normalized
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _normalize_frame(
        self,
        rows: list[list[Any]],
    ) -> pd.DataFrame:
        frame = pd.DataFrame(
            rows,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
        )

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            unit="ms",
            utc=True,
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

        frame = frame.dropna()
        frame = frame.drop_duplicates(subset=["timestamp"])
        frame = frame.sort_values("timestamp")
        frame = frame.reset_index(drop=True)

        return frame

    def _merge_frames(
        self,
        existing: pd.DataFrame | None,
        incoming: pd.DataFrame,
    ) -> pd.DataFrame:
        if existing is None or existing.empty:
            return incoming

        merged = pd.concat(
            [existing, incoming],
            ignore_index=True,
        )

        merged = merged.drop_duplicates(subset=["timestamp"])
        merged = merged.sort_values("timestamp")
        merged = merged.reset_index(drop=True)

        return merged

    def download_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        limit: int = 2000,
        save_parquet: bool = True,
    ) -> DownloadResult:
        self._validate_timeframe(timeframe)

        logger.info(
            "downloading_binance_ohlcv symbol=%s timeframe=%s limit=%s",
            symbol,
            timeframe,
            limit,
        )

        try:
            rows = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )
        except Exception as exc:
            raise BinanceDataError(
                f"binance download failed: {exc}"
            ) from exc

        if not rows:
            raise BinanceDataError(
                "empty OHLCV response from Binance"
            )

        incoming = self._normalize_frame(rows)

        symbol_dir = self._symbol_directory(symbol)

        parquet_path = symbol_dir / f"{timeframe}.parquet"
        csv_path = symbol_dir / f"{timeframe}.csv"

        existing: pd.DataFrame | None = None

        if parquet_path.exists():
            existing = pd.read_parquet(parquet_path)
        elif csv_path.exists():
            existing = pd.read_csv(csv_path)

            if "timestamp" in existing.columns:
                existing["timestamp"] = pd.to_datetime(
                    existing["timestamp"],
                    utc=True,
                )

        merged = self._merge_frames(existing, incoming)

        if save_parquet:
            merged.to_parquet(parquet_path, index=False)
            output_path = str(parquet_path)
        else:
            merged.to_csv(csv_path, index=False)
            output_path = str(csv_path)

        logger.info(
            "saved_market_data rows=%s path=%s",
            len(merged),
            output_path,
        )

        return DownloadResult(
            symbol=symbol,
            timeframe=timeframe,
            rows_downloaded=len(incoming),
            output_path=output_path,
        )
