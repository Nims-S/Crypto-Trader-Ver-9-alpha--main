from __future__ import annotations

from ver9.research.data.market_data import MarketDataLoader
from ver9.research.experiments.tracker import ExperimentTracker
from ver9.research.optimization.guardrails import OptimizationGuardrails
from ver9.research.optimization.search import GridSearchOptimizer
from ver9.research.strategies.sma_cross import SmaCrossStrategy


loader = MarketDataLoader(root="data")

dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

tracker = ExperimentTracker(storage_root="experiments")

optimizer = GridSearchOptimizer(tracker=tracker)

parameter_space = {
    "fast_period": [10, 20, 30],
    "slow_period": [50, 100, 200],
}

result = optimizer.optimize(
    strategy_factory=SmaCrossStrategy,
    parameter_space=parameter_space,
    frame=dataset.frame,
    symbol=dataset.symbol,
    timeframe=dataset.timeframe,
)

print("OPTIMIZATION_RESULT")
print(result)
print()

print("BEST_CANDIDATE")
print(result.best_candidate)
print()

guardrails = OptimizationGuardrails(
    min_trade_count=20,
    max_drawdown_pct=35.0,
    min_sharpe_ratio=0.5,
)

print("TOP_CANDIDATES")

for candidate in result.ranked_candidates[:5]:
    decision = guardrails.evaluate(candidate)

    print(candidate.parameters)
    print(candidate.metrics)
    print(decision)
    print()
