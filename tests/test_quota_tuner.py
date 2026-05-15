from ver9.generation import generate_candidates, generation_quota_report
from ver9.quota_tuner import (
    build_regime_quota_plan,
    infer_regime,
    regime_quota_report,
    tune_family_quotas,
)



def _candidate(symbol: str, family: str, score: float, regime: str = "adaptive"):
    return {
        "symbol": symbol,
        "family": family,
        "validation_score": score,
        "robustness_score": score,
        "regime": regime,
    }



def test_infer_regime_detects_mean_reversion_bias():
    history = [
        _candidate("BTC/USDT", "mean_reversion", 0.9),
        _candidate("ETH/USDT", "mean_reversion", 0.85),
        _candidate("SOL/USDT", "trend", 0.6),
    ]

    regime = infer_regime(history)
    assert regime == "mean_reversion"



def test_family_quota_tuning_boosts_regime_family():
    quotas = tune_family_quotas("mean_reversion")
    assert quotas["mean_reversion"] >= quotas["trend"]



def test_regime_quota_plan_builds_rows():
    plan = build_regime_quota_plan(4, regime="volatility_compression")
    assert plan
    assert any(row["family"] == "volatility_compression" for row in plan)



def test_generation_report_exposes_adaptive_regime():
    history = [
        _candidate("BTC/USDT", "volatility_compression", 0.91, regime="volatility_compression"),
        _candidate("ETH/USDT", "volatility_compression", 0.88, regime="volatility_compression"),
    ]

    report = generation_quota_report(
        3,
        candidate_history=history,
        adaptive=True,
    )

    assert report["adaptive"] is True
    assert report["regime"] == "volatility_compression"



def test_generate_candidates_embeds_regime():
    history = [
        _candidate("BTC/USDT", "mean_reversion", 0.95, regime="mean_reversion"),
    ]

    rows = generate_candidates(
        iterations=2,
        candidate_history=history,
        adaptive=True,
    )

    assert rows
    assert all(row["regime"] == "mean_reversion" for row in rows)



def test_regime_quota_report_has_plan():
    report = regime_quota_report(3, regime="trend")
    payload = report.as_dict()
    assert payload["plan"]
    assert payload["dominant_family"]
