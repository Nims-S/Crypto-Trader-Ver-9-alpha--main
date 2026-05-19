from __future__ import annotations

from ver9.research.data.market_data import MarketDataLoader
from ver9.research.features.pipeline import FeaturePipeline
from ver9.research.features.store import FeatureStore


loader = MarketDataLoader(root="data")

dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

pipeline = FeaturePipeline(
    rsi_period=14,
    roc_period=14,
    ema_fast=50,
    ema_slow=200,
    volatility_window=50,
)

result = pipeline.build(dataset.frame)

print("FEATURE_PIPELINE_RESULT")
print(f"rows={len(result.frame)}")
print(f"features={result.feature_columns}")
print(f"dropped_rows={result.dropped_rows}")
print()

store = FeatureStore(storage_root="feature_store")

stored = store.save_feature_set(
    strategy_family="ml_pattern_matching",
    symbol=dataset.symbol,
    timeframe=dataset.timeframe,
    frame=result.frame,
    feature_columns=result.feature_columns,
    version="v1",
    tags=["baseline", "research", "btc"],
)

print("FEATURE_STORE_RESULT")
print(stored)
