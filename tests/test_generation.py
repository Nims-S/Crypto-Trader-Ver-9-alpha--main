from ver9.generation import (
    build_generation_plan,
    generate_candidates,
    generation_quota_report,
)



def test_generation_plan_builds_rows():
    plan = build_generation_plan(3)
    assert plan
    assert all("family" in row for row in plan)
    assert all("symbol" in row for row in plan)
    assert all("count" in row for row in plan)



def test_generate_candidates_respects_custom_family_quota():
    rows = generate_candidates(
        iterations=3,
        family_quota={
            "mean_reversion": 1,
            "volatility_compression": 0,
            "trend": 0,
        },
    )
    assert rows
    assert all(row["family"] == "mean_reversion" for row in rows)



def test_generate_candidates_respects_symbol_quota():
    rows = generate_candidates(
        iterations=3,
        symbol_quota={
            "BTC/USDT": 1,
            "ETH/USDT": 0,
            "SOL/USDT": 0,
        },
    )
    assert rows
    assert all(row["symbol"] == "BTC/USDT" for row in rows)



def test_generation_quota_report_has_totals():
    report = generation_quota_report(2)
    assert report["total_planned"] > 0
    assert "family_counts" in report
    assert "symbol_counts" in report
