from __future__ import annotations

from ver9.research.backtesting.engine import BacktestEngine
from ver9.research.data.market_data import MarketDataLoader
from ver9.research.metrics.performance import build_report
from ver9.research.strategies.lorentzian_classifier import (
    LorentzianClassificationStrategy,
)
from ver9.research.validation.walkforward import WalkForwardValidator


"""
Minimal end-to-end research pipeline.

Usage:
    1. Place OHLCV data at:
       data/btc_usdt/1h.parquet
       OR
       data/btc_usdt/1h.csv

    2. Run:
       python -m ver9.research.examples.run_lorentzian_research
"""


loader = MarketDataLoader(root="data")

dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

strategy = LorentzianClassificationStrategy()

engine = BacktestEngine(
    fee_bps=10.0,
    slippage_bps=5.0,
    initial_capital=10000.0,
)

result = engine.run(
    strategy=strategy,
    frame=dataset.frame,
    symbol=dataset.symbol,
    timeframe=dataset.timeframe,
)

report = build_report(result)

validator = WalkForwardValidator(
    train_size=1000,
    test_size=250,
    step_size=250,
)

walkforward = validator.validate(
    strategy=strategy,
    frame=dataset.frame,
    symbol=dataset.symbol,
    timeframe=dataset.timeframe,
    engine=engine,
)

print("=== BACKTEST REPORT ===")
print(report)
print()
print("=== WALKFORWARD WINDOWS ===")
print(len(walkforward.windows))
print()
print("=== WALKFORWARD RESULTS ===")

for idx, wf_result in enumerate(walkforward.test_results, start=1):
    print(
        idx,
        wf_result.total_return_pct,
        wf_result.sharpe_ratio,
        wf_result.max_drawdown_pct,
    )
