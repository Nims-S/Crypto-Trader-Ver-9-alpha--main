from __future__ import annotations

from collections import Counter

from ver9.research.data.market_data import MarketDataLoader
from ver9.research.regime.classifier import (
    MarketRegimeClassifier,
)
from ver9.research.regime.router import StrategyRegimeRouter
from ver9.research.strategies.lorentzian_classifier import (
    LorentzianClassificationStrategy,
)
from ver9.research.strategies.sma_cross import (
    SmaCrossStrategy,
)


loader = MarketDataLoader(root="data")

dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

classifier = MarketRegimeClassifier(
    volatility_window=50,
    trend_window=200,
    liquidity_window=50,
)

regimes = classifier.classify(dataset.frame)

print("TOTAL_REGIME_STATES")
print(len(regimes))
print()

volatility_counts = Counter(
    regime.volatility_regime
    for regime in regimes
)

trend_counts = Counter(
    regime.trend_regime
    for regime in regimes
)

print("VOLATILITY_REGIMES")
print(dict(volatility_counts))
print()

print("TREND_REGIMES")
print(dict(trend_counts))
print()

latest_regime = regimes[-1]

strategies = [
    SmaCrossStrategy(),
    LorentzianClassificationStrategy(),
]

router = StrategyRegimeRouter()

routing = router.route(
    strategies=strategies,
    regime=latest_regime,
)

print("LATEST_REGIME")
print(latest_regime)
print()

print("ROUTING_DECISION")
print(routing)
