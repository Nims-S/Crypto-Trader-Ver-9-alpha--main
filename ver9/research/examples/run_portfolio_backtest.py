from __future__ import annotations

from ver9.research.backtesting.portfolio_engine import (
    PortfolioBacktestEngine,
)
from ver9.research.data.market_data import MarketDataLoader
from ver9.research.strategies.lorentzian_classifier import (
    LorentzianClassificationStrategy,
)
from ver9.research.strategies.sma_cross import (
    SmaCrossStrategy,
)


"""
Portfolio-level strategy simulation.

Usage:
    python -m ver9.research.examples.run_portfolio_backtest
"""


loader = MarketDataLoader(root="data")

btc_dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

strategies = [
    SmaCrossStrategy(
        fast_period=20,
        slow_period=50,
    ),
    LorentzianClassificationStrategy(),
]

engine = PortfolioBacktestEngine(
    initial_capital=10000.0,
    max_positions=5,
    max_symbol_exposure_pct=0.35,
    risk_per_trade_pct=0.02,
    fee_bps=10.0,
    slippage_bps=5.0,
    holding_period_bars=4,
)

result = engine.run(
    strategies=strategies,
    frame=btc_dataset.frame,
    symbol=btc_dataset.symbol,
    timeframe=btc_dataset.timeframe,
)

print("=== PORTFOLIO BACKTEST ===")
print(result)
print()
print("=== EQUITY CURVE POINTS ===")
print(len(result.equity_curve))
print()
print("=== TRADES ===")
print(result.total_trades)
print()
print("=== ACTIVE STRATEGIES ===")
print(result.active_strategies)
