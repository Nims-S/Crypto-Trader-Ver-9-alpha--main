from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import ver9.daemon as daemon
import ver9.registry as registry
import ver9.state as state
from ver9.basket_optimizer import BasketOptimizer, basket_summary


@dataclass
class _FakeExecutionSummary:
    payload: dict

    def as_dict(self) -> dict:
        return self.payload



def _candidate(strategy_id: str, family: str, symbol: str, robustness: float = 0.82) -> dict[str, object]:
    return {
        "strategy_id": strategy_id,
        "family": family,
        "symbol": symbol,
        "regime": family,
        "robustness_score": robustness,
        "profit_factor": 1.8,
        "return_pct": 12.0,
        "max_drawdown_pct": -4.0,
        "validation_passed": True,
        "validation_score": 2.5,
        "status": "validated",
        "updated_at": "2026-05-18T00:00:00+00:00",
    }



def test_registry_recovery_preserves_entries_and_atomic_save(tmp_path, monkeypatch):
    registry_path = tmp_path / "ver9_registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    registry_path.write_text(
        '{"created_at":"x","updated_at":"x","entries":{"keep":{"strategy_id":"keep","family":"trend","regime":"trend","symbol":"BTC/USDT","status":"validated"}}} trailing-data',
        encoding="utf-8",
    )

    payload = registry.load_registry()

    assert payload["entries"]["keep"]["strategy_id"] == "keep"
    assert payload["entries"]["keep"]["status"] == "validated"
    assert registry_path.exists()
    parsed = json.loads(registry_path.read_text(encoding="utf-8"))
    assert parsed["entries"]["keep"]["strategy_id"] == "keep"



def test_strict_basket_rejects_undersized_pool_and_reports_basket_size() -> None:
    rows = [
        _candidate("btc_mr", "mean_reversion", "BTC/USDT", 0.9),
        _candidate("eth_vc", "volatility_compression", "ETH/USDT", 0.82),
    ]

    strict = BasketOptimizer(max_positions=3, min_positions=3, soft_fill=False)
    assert strict.allocate(rows) == []

    summary = basket_summary(rows, max_positions=3, min_positions=2, soft_fill=False)
    assert "basket_size" in summary
    assert summary["basket_size"] == 2
    assert summary["selected"]



def test_recovery_cleanup_removes_quarantine_record(tmp_path, monkeypatch):
    state_path = tmp_path / "runtime_state.json"
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(state, "STATE_PATH", state_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    strategy_id = "sol_breakout_alpha"
    state.quarantine_strategy(strategy_id, "risk_failure")

    first = state.recover_strategy(strategy_id)
    second = state.recover_strategy(strategy_id)
    third = state.recover_strategy(strategy_id)
    fourth = state.recover_strategy(strategy_id)

    assert first["status"] == "quarantined"
    assert second["status"] == "probationary"
    assert third["status"] == "probationary"
    assert fourth["status"] == "active"

    summary = state.summarize_state()
    assert summary["quarantined_count"] == 0
    assert summary["strategy_status_counts"].get("active", 0) >= 1
    assert state.is_quarantined(strategy_id) is False

    registry_payload = registry.load_registry()
    assert registry_payload["entries"][strategy_id]["status"] == "active"



def test_daemon_reports_thin_basket_and_selected_source(tmp_path, monkeypatch):
    state_path = tmp_path / "runtime_state.json"
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(state, "STATE_PATH", state_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    registry.upsert_candidate(
        {
            "strategy_id": "mean_reversion_sol_usdt_0",
            "family": "mean_reversion",
            "regime": "mean_reversion",
            "symbol": "SOL/USDT",
            "status": "deployable",
            "validation_passed": True,
            "validation_score": 2.75,
            "robustness_score": 0.88,
            "profit_factor": 2.1,
            "return_pct": 13.4,
            "max_drawdown_pct": -3.1,
            "trades": 120,
            "execution_quality_score": 0.99,
            "capital_multiplier": 1.0,
            "updated_at": "2026-05-18T00:00:00+00:00",
        }
    )

    monkeypatch.setattr(daemon, "allocate", lambda candidates, **kwargs: [dict(candidates[0], allocation_pct=0.4, allocation_weight=0.4)])
    monkeypatch.setattr(
        daemon,
        "execute_allocations",
        lambda allocations, **kwargs: _FakeExecutionSummary(
            {
                "mode": "paper",
                "requested_orders": 1,
                "filled_orders": 1,
                "rejected_orders": 0,
                "fill_rate": 1.0,
                "average_slippage_bps": 0.0,
                "capital_committed": 4000.0,
                "fills": [
                    {
                        "strategy_id": allocations[0]["strategy_id"],
                        "symbol": allocations[0]["symbol"],
                        "side": "buy",
                        "quantity": 40.0,
                        "fill_price": 100.0,
                    }
                ],
                "rejections": [],
                "acceptance_history": [
                    {
                        "strategy_id": allocations[0]["strategy_id"],
                        "symbol": allocations[0]["symbol"],
                        "side": "buy",
                        "requested_quantity": 40.0,
                        "expected_price": 100.0,
                        "fill_price": 100.0,
                        "accepted": True,
                        "fill_ratio": 1.0,
                        "slippage_bps": 0.0,
                        "rejection_reason": None,
                    }
                ],
                "rejection_telemetry": {"reasons": {}, "total_rejections": 0, "unique_strategies_rejected": 0},
                "per_strategy_stats": {
                    allocations[0]["strategy_id"]: {
                        "requested_orders": 1,
                        "filled_orders": 1,
                        "rejected_orders": 0,
                        "fill_rate": 1.0,
                        "average_slippage_bps": 0.0,
                        "execution_quality_score": 1.0,
                    }
                },
                "equity_before": 10000.0,
                "equity_after": 9996.0,
                "execution_quality_score": 1.0,
            }
        ),
    )

    cycle = daemon.run_daemon_once(capital=10000.0, max_positions=3, live=False)

    assert cycle["selected_source"] == "deployable"
    assert cycle["selected_source_count"] == 1
    assert cycle["thin_basket_note"] == "thin_basket_constrained_mode:deployable"
    assert cycle["execution_signal"]["reason"] == "execution_full_fill"
    assert cycle["transition_summary"]
    assert cycle["transition_summary"][0]["to"] == "active"
