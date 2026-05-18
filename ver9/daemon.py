from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from .execution import execute_allocations
from .portfolio import allocate
from .registry import list_candidates
from .risk import RiskMonitor
from .state import (
    append_cycle,
    append_execution,
    append_risk_event,
    quarantine_strategy,
    recover_strategy,
    summarize_state,
)


class DaemonError(RuntimeError):
    pass


class Version9Daemon:
    def __init__(
        self,
        *,
        capital: float = 10000.0,
        max_positions: int = 3,
        live: bool = False,
        cycle_interval_seconds: float = 5.0,
        max_cycles: int | None = None,
    ) -> None:
        self.capital = capital
        self.max_positions = max_positions
        self.live = live
        self.cycle_interval_seconds = cycle_interval_seconds
        self.max_cycles = max_cycles
        self.risk_monitor = RiskMonitor()
        self.running = False

    def _eligible_candidates(self) -> list[dict[str, Any]]:
        candidates = list_candidates(status="deployable")
        if not candidates:
            candidates = list_candidates(status="probationary")
        if not candidates:
            candidates = list_candidates(status="validated")

        filtered: list[dict[str, Any]] = []
        for row in candidates:
            strategy_id = str(row.get("strategy_id") or "")
            if not strategy_id:
                continue
            if row.get("status") == "retired":
                continue
            filtered.append(row)
        return filtered

    def _execution_signal(self, execution: Any) -> tuple[bool, str, float]:
        fill_rate = float(getattr(execution, "fill_rate", 0.0) or 0.0)
        rejected_orders = int(getattr(execution, "rejected_orders", 0) or 0)
        accepted_orders = int(getattr(execution, "filled_orders", 0) or 0)

        if accepted_orders == 0 and rejected_orders > 0:
            return False, "execution_all_rejected", fill_rate
        if fill_rate < 0.50:
            return False, "execution_low_fill_rate", fill_rate
        if fill_rate < 0.85:
            return True, "execution_partial_fill", fill_rate
        return True, "execution_full_fill", fill_rate

    def build_cycle(self) -> dict[str, Any]:
        candidates = self._eligible_candidates()
        portfolio = allocate(candidates, max_positions=self.max_positions)
        execution = execute_allocations(portfolio, capital=self.capital, live=self.live)

        successful_orders = int(execution.filled_orders)
        rejected_orders = int(execution.rejected_orders)
        fill_rate = float(execution.fill_rate or 0.0)

        execution_approved, execution_reason, signal_fill_rate = self._execution_signal(execution)
        if fill_rate >= 0.85 and successful_orders > 0:
            portfolio_drawdown = -1.5
            volatility_score = 0.4
            loss_streak = 0
        elif fill_rate >= 0.50:
            portfolio_drawdown = -4.5
            volatility_score = 0.62
            loss_streak = 1
        else:
            portfolio_drawdown = -10.5
            volatility_score = 0.92
            loss_streak = 3

        risk_state = self.risk_monitor.evaluate_portfolio(
            portfolio_drawdown_pct=portfolio_drawdown,
            rolling_loss_streak=loss_streak,
            volatility_regime_score=volatility_score,
        )

        transition_summary: list[dict[str, Any]] = []
        accepted_strategy_ids = {
            str(row.get("strategy_id") or "")
            for row in getattr(execution, "acceptance_history", [])
            if isinstance(row, dict) and row.get("accepted")
        }
        rejection_by_strategy = {
            str(row.get("strategy_id") or ""): str(row.get("rejection_reason") or "unfilled")
            for row in getattr(execution, "acceptance_history", [])
            if isinstance(row, dict) and not row.get("accepted")
        }

        for allocation in portfolio:
            strategy_id = str(allocation.get("strategy_id") or "")
            if not strategy_id:
                continue

            if not risk_state.approved or strategy_id in rejection_by_strategy:
                reason = rejection_by_strategy.get(strategy_id) or risk_state.reason or execution_reason
                quarantine_strategy(strategy_id, reason=f"daemon_{reason}")
                transition_summary.append({"strategy_id": strategy_id, "from": allocation.get("status"), "to": "quarantined", "reason": reason})
                continue

            if strategy_id in accepted_strategy_ids:
                new_entry = recover_strategy(strategy_id, reason=f"daemon_{execution_reason}")
                transition_summary.append({"strategy_id": strategy_id, "from": allocation.get("status"), "to": new_entry.get("status"), "reason": execution_reason})
            else:
                quarantine_strategy(strategy_id, reason=f"daemon_{execution_reason}_missing_fill")
                transition_summary.append({"strategy_id": strategy_id, "from": allocation.get("status"), "to": "quarantined", "reason": execution_reason})

        cycle = {
            "timestamp": datetime.now(UTC).isoformat(),
            "portfolio": portfolio,
            "execution": execution.as_dict(),
            "risk": risk_state.as_dict(),
            "execution_signal": {
                "approved": execution_approved,
                "reason": execution_reason,
                "fill_rate": round(signal_fill_rate, 6),
                "filled_orders": successful_orders,
                "rejected_orders": rejected_orders,
            },
            "transition_summary": transition_summary,
            "state_summary": summarize_state(),
        }

        append_cycle(cycle)
        append_execution(execution.as_dict())
        append_risk_event(risk_state.as_dict())

        return cycle

    def run_once(self) -> dict[str, Any]:
        return self.build_cycle()

    def run_forever(self) -> list[dict[str, Any]]:
        self.running = True
        cycles: list[dict[str, Any]] = []
        completed = 0

        while self.running:
            cycle = self.build_cycle()
            cycles.append(cycle)
            completed += 1

            if self.max_cycles is not None and completed >= self.max_cycles:
                break

            time.sleep(self.cycle_interval_seconds)

        self.running = False
        return cycles

    def stop(self) -> None:
        self.running = False


def run_daemon_once(*, capital: float = 10000.0, max_positions: int = 3, live: bool = False) -> dict[str, Any]:
    daemon = Version9Daemon(capital=capital, max_positions=max_positions, live=live)
    return daemon.run_once()


def run_daemon_forever(
    *,
    capital: float = 10000.0,
    max_positions: int = 3,
    live: bool = False,
    cycle_interval_seconds: float = 5.0,
    max_cycles: int | None = None,
) -> list[dict[str, Any]]:
    daemon = Version9Daemon(
        capital=capital,
        max_positions=max_positions,
        live=live,
        cycle_interval_seconds=cycle_interval_seconds,
        max_cycles=max_cycles,
    )
    return daemon.run_forever()
