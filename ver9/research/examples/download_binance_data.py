from __future__ import annotations

from ver9.research.data.connectors.binance import (
    BinanceHistoricalDownloader,
)
from ver9.research.data.validation import MarketDataValidator
from ver9.research.data.market_data import MarketDataLoader


"""
Download Binance market data and validate integrity.

Usage:
    python -m ver9.research.examples.download_binance_data
"""


downloader = BinanceHistoricalDownloader(data_root="data")

result = downloader.download_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
    limit=5000,
)

print("DOWNLOAD_RESULT")
print(result)
print()

loader = MarketDataLoader(root="data")

dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

validator = MarketDataValidator()

report = validator.validate(dataset.frame)

print("VALIDATION_REPORT")
print(report)
