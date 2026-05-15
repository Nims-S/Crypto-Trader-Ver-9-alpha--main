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
    is_quarantined,
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
            if strategy_id and is_quarantined(strategy_id):
                continue
            filtered.append(row)
        return filtered

    def build_cycle(self) -> dict[str, Any]:
        candidates = self._eligible_candidates()

        portfolio = allocate(candidates, max_positions=self.max_positions)
        execution = execute_allocations(portfolio, capital=self.capital, live=self.live)

        successful_orders = len(execution.filled_orders)
        portfolio_drawdown = -2.5 if successful_orders else -8.0
        volatility_score = 0.55 if successful_orders else 0.95
        loss_streak = 0 if successful_orders else 2

        risk_state = self.risk_monitor.evaluate_portfolio(
            portfolio_drawdown_pct=portfolio_drawdown,
            rolling_loss_streak=loss_streak,
            volatility_regime_score=volatility_score,
        )

        for allocation in portfolio:
            strategy_id = str(allocation.get("strategy_id") or "")
            if not strategy_id:
                continue
            if risk_state.approved:
                recover_strategy(strategy_id, reason="approved_cycle")
            else:
                quarantine_strategy(strategy_id, risk_state.reason)

        cycle = {
            "timestamp": datetime.now(UTC).isoformat(),
            "portfolio": portfolio,
            "execution": execution.as_dict(),
            "risk": risk_state.as_dict(),
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
