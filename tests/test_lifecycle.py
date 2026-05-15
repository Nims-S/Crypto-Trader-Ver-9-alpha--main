from ver9.lifecycle import (
    auto_promote,
    can_enter_deployable_basket,
    can_enter_probationary_basket,
)



def _candidate(symbol: str, family: str, robustness: float, pf: float):
    return {
        "strategy_id": f"{family}_{symbol}",
        "symbol": symbol,
        "family": family,
        "regime": "adaptive",
        "robustness_score": robustness,
        "profit_factor": pf,
        "max_drawdown_pct": -5.0,
        "validation_passed": True,
        "validation_score": 0.8,
        "status": "candidate",
    }



def test_probationary_requires_quality_thresholds():
    row = _candidate("BTC/USDT", "mean_reversion", 0.9, 2.1)
    assert can_enter_probationary_basket(row)



def test_deployable_requires_stronger_thresholds():
    row = _candidate("ETH/USDT", "volatility_compression", 0.93, 2.4)
    assert can_enter_deployable_basket(row)



def test_auto_promote_prefers_diverse_additions():
    existing = {
        "selected_count": 2,
        "diversity_score": 1.25,
        "symbol_counts": {"BTC": 1, "ETH": 1},
        "family_counts": {
            "mean_reversion": 1,
            "volatility_compression": 1,
        },
        "regime_counts": {"adaptive": 2},
    }

    row = _candidate("SOL/USDT", "trend", 0.94, 2.5)
    promoted = auto_promote(row, basket_context=existing)

    assert promoted["status"] in {"probationary", "deployable"}



def test_auto_promote_rejects_weak_candidate():
    weak = _candidate("BTC/USDT", "mean_reversion", 0.5, 1.1)
    promoted = auto_promote(weak)
    assert promoted["status"] == "candidate"
