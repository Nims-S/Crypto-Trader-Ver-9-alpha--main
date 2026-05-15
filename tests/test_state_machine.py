from __future__ import annotations

import tempfile
from pathlib import Path

import ver9.state as state


class TempState:
    def __enter__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original = state.STATE_PATH
        state.STATE_PATH = Path(self.tmpdir.name) / "runtime_state.json"
        return state.STATE_PATH

    def __exit__(self, exc_type, exc, tb):
        state.STATE_PATH = self.original
        self.tmpdir.cleanup()


def test_quarantine_trigger() -> None:
    with TempState():
        result = state.quarantine_strategy("btc_mr_alpha", "risk_failure")
        assert result["status"] == "quarantined"
        assert state.is_quarantined("btc_mr_alpha") is True

        summary = state.summarize_state()
        assert summary["quarantined_count"] == 1


def test_recovery_requires_multiple_cycles() -> None:
    with TempState():
        state.quarantine_strategy("eth_mr_alpha", "risk_failure")

        first = state.recover_strategy("eth_mr_alpha")
        assert first["status"] == "quarantined"

        second = state.recover_strategy("eth_mr_alpha")
        assert second["status"] == "probationary"

        third = state.recover_strategy("eth_mr_alpha")
        assert third["status"] == "probationary"

        fourth = state.recover_strategy("eth_mr_alpha")
        assert fourth["status"] == "active"

        assert state.is_quarantined("eth_mr_alpha") is False


def test_state_summary_counts() -> None:
    with TempState():
        state.quarantine_strategy("sol_breakout_alpha", "volatility_failure")
        state.recover_strategy("sol_breakout_alpha")
        state.recover_strategy("sol_breakout_alpha")

        summary = state.summarize_state()
        counts = summary["strategy_status_counts"]

        assert isinstance(counts, dict)
        assert counts.get("probationary", 0) >= 1
