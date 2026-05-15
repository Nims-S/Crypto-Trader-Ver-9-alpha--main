from ver9.basket_optimizer import BasketOptimizer, basket_summary
from ver9.diversity import basket_diversity_score



def _candidate(strategy_id: str, family: str, symbol: str, robustness: float):
    return {
        "strategy_id": strategy_id,
        "family": family,
        "symbol": symbol,
        "regime": "adaptive",
        "robustness_score": robustness,
        "profit_factor": 1.8,
        "return_pct": 12.0,
        "max_drawdown_pct": -4.0,
        "validation_passed": True,
        "status": "validated",
    }



def test_probationary_basket_builds_when_soft_fill_enabled():
    optimizer = BasketOptimizer(
        max_positions=3,
        min_positions=2,
        soft_fill=True,
    )

    rows = [
        _candidate("btc_mr", "mean_reversion", "BTC/USDT", 0.9),
        _candidate("eth_vc", "volatility_compression", "ETH/USDT", 0.82),
    ]

    basket = optimizer.allocate(rows)
    assert len(basket) >= 2



def test_strict_basket_can_reject_small_pool():
    optimizer = BasketOptimizer(
        max_positions=3,
        min_positions=3,
        soft_fill=False,
    )

    rows = [
        _candidate("btc_mr", "mean_reversion", "BTC/USDT", 0.9),
        _candidate("eth_vc", "volatility_compression", "ETH/USDT", 0.82),
    ]

    basket = optimizer.allocate(rows)
    assert basket == []



def test_basket_summary_reports_diversity():
    rows = [
        _candidate("btc_mr", "mean_reversion", "BTC/USDT", 0.9),
        _candidate("eth_vc", "volatility_compression", "ETH/USDT", 0.82),
        _candidate("sol_trend", "trend", "SOL/USDT", 0.8),
    ]

    summary = basket_summary(rows)
    assert summary["basket_size"] >= 2
    assert summary["diversity_score"] > 0



def test_diversity_score_rewards_multi_symbol_mix():
    diversified = [
        _candidate("btc", "mean_reversion", "BTC/USDT", 0.8),
        _candidate("eth", "trend", "ETH/USDT", 0.8),
        _candidate("sol", "volatility_compression", "SOL/USDT", 0.8),
    ]

    concentrated = [
        _candidate("btc_a", "mean_reversion", "BTC/USDT", 0.8),
        _candidate("btc_b", "mean_reversion", "BTC/USDT", 0.8),
        _candidate("btc_c", "mean_reversion", "BTC/USDT", 0.8),
    ]

    assert basket_diversity_score(diversified) > basket_diversity_score(concentrated)
