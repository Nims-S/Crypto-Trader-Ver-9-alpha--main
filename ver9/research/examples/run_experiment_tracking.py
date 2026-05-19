from __future__ import annotations

from dataclasses import asdict

from ver9.research.backtesting.portfolio_engine import (
    PortfolioBacktestEngine,
)
from ver9.research.data.market_data import MarketDataLoader
from ver9.research.experiments.ranking import ExperimentRanker
from ver9.research.experiments.tracker import ExperimentTracker
from ver9.research.strategies.lorentzian_classifier import (
    LorentzianClassificationStrategy,
)
from ver9.research.validation.walkforward import WalkForwardValidator


loader = MarketDataLoader(root="data")

btc_dataset = loader.load_ohlcv(
    symbol="BTC/USDT",
    timeframe="1h",
)

strategy = LorentzianClassificationStrategy()

portfolio_engine = PortfolioBacktestEngine(
    initial_capital=10000.0,
    max_positions=5,
)

portfolio_result = portfolio_engine.run(
    strategies=[strategy],
    frame=btc_dataset.frame,
    symbol=btc_dataset.symbol,
    timeframe=btc_dataset.timeframe,
)

validator = WalkForwardValidator(
    train_size=1000,
    test_size=250,
    step_size=250,
)

walkforward_result = validator.validate(
    strategy=strategy,
    frame=btc_dataset.frame,
    symbol=btc_dataset.symbol,
    timeframe=btc_dataset.timeframe,
    engine=portfolio_engine,
)

tracker = ExperimentTracker(storage_root="experiments")

record = tracker.create_experiment(
    strategy_id=strategy.strategy_id,
    strategy_family=strategy.family,
    symbol=btc_dataset.symbol,
    timeframe=btc_dataset.timeframe,
    dataset_rows=len(btc_dataset.frame),
    parameters={
        "neighbors_count": strategy.config.neighbors_count,
        "lookback_window": strategy.config.lookback_window,
        "future_bars": strategy.config.future_bars,
    },
    metrics={
        "total_return_pct": portfolio_result.total_return_pct,
        "sharpe_ratio": portfolio_result.sharpe_ratio,
        "max_drawdown_pct": portfolio_result.max_drawdown_pct,
        "trade_count": portfolio_result.total_trades,
    },
    walkforward_summary={
        "window_count": len(walkforward_result.windows),
        "results": [
            {
                "total_return_pct": result.total_return_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
            }
            for result in walkforward_result.test_results
        ],
    },
    tags=["lorentzian", "portfolio_backtest", "walkforward"],
    notes="initial integrated research run",
)

path = tracker.save(record)

print("EXPERIMENT_SAVED")
print(path)
print()

records = tracker.load_all(
    strategy_id=strategy.strategy_id,
)

ranker = ExperimentRanker()

ranked = ranker.rank(records)

print("RANKED_EXPERIMENTS")

for item in ranked:
    print(asdict(item))
