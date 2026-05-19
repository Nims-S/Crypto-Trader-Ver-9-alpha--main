from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .execution import ExecutionSummary, execute_allocations
from .lifecycle import build_transition_record
from .models import AllocationDecision, LifecycleTransition
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
from .utils.serialization import serialize_model


class DaemonError(RuntimeError):
    pass


@dataclass(slots=True)
class ExecutionSignal:
    approved: bool
    reason: str
    fill_rate: float
    filled_orders: int
    rejected_orders: int


@dataclass(slots=True)
class RuntimeCycle:
    timestamp: str
    candidate_count: int
    candidate_source_counts: dict[str, int]
    selected_count: int
    selected_source: str
    selected_source_count: int
    selection_reason: str
    thin_basket_note: str | None
    portfolio: list[AllocationDecision]
    execution: dict[str, Any]
    risk: dict[str, Any]
    execution_signal: ExecutionSignal
    transition_summary: list[LifecycleTransition] = field(default_factory=list)
    state_summary: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return serialize_model(self)


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

    def _candidate_source_counts(self) -> dict[str, int]:
        return {
            "deployable": len(list_candidates(status="deployable")),
            "probationary": len(list_candidates(status="probationary")),
            "validated": len(list_candidates(status="validated")),
        }

    def _eligible_candidates(self) -> tuple[list[dict[str, Any]], dict[str, int], str]:
        source_counts = self._candidate_source_counts()
        selection_reason = "deployable"

        for status in ("deployable", "probationary", "validated"):
            candidates = list_candidates(status=status)
            filtered: list[dict[str, Any]] = []

            for row in candidates:
                strategy_id = str(row.get("strategy_id") or "")

                if not strategy_id:
                    continue

                if row.get("status") == "retired":
                    continue

                filtered.append(row)

            if filtered:
                selection_reason = status
                return filtered, source_counts, selection_reason

        return [], source_counts, "no_candidates"

    def _execution_signal(self, execution: ExecutionSummary) -> ExecutionSignal:
        fill_rate = float(getattr(execution, "fill_rate", 0.0) or 0.0)
        rejected_orders = int(getattr(execution, "rejected_orders", 0) or 0)
        accepted_orders = int(getattr(execution, "filled_orders", 0) or 0)

        if accepted_orders == 0 and rejected_orders > 0:
            return ExecutionSignal(False, "execution_all_rejected", fill_rate, accepted_orders, rejected_orders)

        if fill_rate < 0.50:
            return ExecutionSignal(False, "execution_low_fill_rate", fill_rate, accepted_orders, rejected_orders)

        if fill_rate < 0.85:
            return ExecutionSignal(True, "execution_partial_fill", fill_rate, accepted_orders, rejected_orders)

        return ExecutionSignal(True, "execution_full_fill", fill_rate, accepted_orders, rejected_orders)

    def _selection_failure_reason(self, candidate_count: int, selected_count: int) -> str:
        if candidate_count <= 0:
            return "no_candidates"

        if selected_count <= 0:
            return "selection_starved"

        if selected_count < self.max_positions:
            return "selection_starved"

        return "selection_complete"

    def _thin_basket_note(
        self,
        candidate_count: int,
        selected_count: int,
        selection_reason: str,
    ) -> str | None:
        if candidate_count == 1:
            return f"thin_basket_constrained_mode:{selection_reason}"

        if selected_count == 1:
            return f"thin_basket_single_position:{selection_reason}"

        return None

    def _empty_execution(self) -> dict[str, Any]:
        return {
            "mode": "paper" if not self.live else "live",
            "requested_orders": 0,
            "filled_orders": 0,
            "rejected_orders": 0,
            "fill_rate": 0.0,
            "average_slippage_bps": 0.0,
            "capital_committed": 0.0,
            "fills": [],
            "rejections": [],
            "acceptance_history": [],
            "per_strategy_stats": {},
            "rejection_telemetry": {
                "reasons": {},
                "total_rejections": 0,
                "unique_strategies_rejected": 0,
            },
        }

    def _build_transition_summary(
        self,
        portfolio: list[AllocationDecision],
        execution: ExecutionSummary,
        risk_state: Any,
        execution_signal: ExecutionSignal,
    ) -> list[LifecycleTransition]:
        transition_summary: list[LifecycleTransition] = []

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
            strategy_id = allocation.strategy_id

            if not strategy_id:
                continue

            current_status = str(allocation.metadata.get("status") or "unknown")

            if not risk_state.approved or strategy_id in rejection_by_strategy:
                reason = (
                    rejection_by_strategy.get(strategy_id)
                    or risk_state.reason
                    or execution_signal.reason
                )

                quarantine_strategy(strategy_id, reason=f"daemon_{reason}")

                transition_summary.append(
                    build_transition_record(
                        strategy_id=strategy_id,
                        from_status=current_status,
                        to_status="quarantined",
                        reason=reason,
                    )
                )

                continue

            if strategy_id in accepted_strategy_ids:
                new_entry = recover_strategy(
                    strategy_id,
                    reason=f"daemon_{execution_signal.reason}",
                )

                transition_summary.append(
                    build_transition_record(
                        strategy_id=strategy_id,
                        from_status=current_status,
                        to_status=str(new_entry.get("status") or current_status),
                        reason=execution_signal.reason,
                    )
                )

                continue

            quarantine_strategy(
                strategy_id,
                reason=f"daemon_{execution_signal.reason}_missing_fill",
            )

            transition_summary.append(
                build_transition_record(
                    strategy_id=strategy_id,
                    from_status=current_status,
                    to_status="quarantined",
                    reason=execution_signal.reason,
                )
            )

        return transition_summary

    def _persist_cycle(self, cycle: RuntimeCycle) -> None:
        payload = cycle.as_dict()

        append_cycle(payload)
        append_execution(payload["execution"])
        append_risk_event(payload["risk"])

    def build_cycle(self) -> dict[str, Any]:
        candidates, source_counts, selection_reason = self._eligible_candidates()

        candidate_count = len(candidates)
        effective_min_positions = 1 if candidate_count < 2 else 2

        portfolio = allocate(
            candidates,
            max_positions=self.max_positions,
            min_positions=effective_min_positions,
        )

        selected_count = len(portfolio)

        selected_source_count = source_counts.get(
            selection_reason,
            candidate_count,
        )

        thin_basket_note = self._thin_basket_note(
            candidate_count,
            selected_count,
            selection_reason,
        )

        if selected_count <= 0:
            failure_reason = self._selection_failure_reason(
                candidate_count,
                selected_count,
            )

            execution_signal = ExecutionSignal(
                approved=False,
                reason=failure_reason,
                fill_rate=0.0,
                filled_orders=0,
                rejected_orders=0,
            )

            cycle = RuntimeCycle(
                timestamp=datetime.now(UTC).isoformat(),
                candidate_count=candidate_count,
                candidate_source_counts=source_counts,
                selected_count=selected_count,
                selected_source=selection_reason,
                selected_source_count=selected_source_count,
                selection_reason=(
                    selection_reason
                    if candidate_count > 0
                    else failure_reason
                ),
                thin_basket_note=thin_basket_note,
                portfolio=[],
                execution=self._empty_execution(),
                risk={
                    "approved": False,
                    "reason": failure_reason,
                },
                execution_signal=execution_signal,
                transition_summary=[],
            )

            self._persist_cycle(cycle)

            cycle.state_summary = summarize_state()
            return cycle.as_dict()

        execution = execute_allocations(
            portfolio,
            capital=self.capital,
            live=self.live,
        )

        execution_signal = self._execution_signal(execution)

        if execution_signal.fill_rate >= 0.85 and execution_signal.filled_orders > 0:
            portfolio_drawdown = -1.5
            volatility_score = 0.4
            loss_streak = 0
        elif execution_signal.fill_rate >= 0.50:
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

        transition_summary = self._build_transition_summary(
            portfolio=portfolio,
            execution=execution,
            risk_state=risk_state,
            execution_signal=execution_signal,
        )

        cycle = RuntimeCycle(
            timestamp=datetime.now(UTC).isoformat(),
            candidate_count=candidate_count,
            candidate_source_counts=source_counts,
            selected_count=selected_count,
            selected_source=selection_reason,
            selected_source_count=selected_source_count,
            selection_reason=selection_reason,
            thin_basket_note=thin_basket_note,
            portfolio=portfolio,
            execution=execution.as_dict(),
            risk=risk_state.as_dict(),
            execution_signal=execution_signal,
            transition_summary=transition_summary,
        )

        self._persist_cycle(cycle)

        cycle.state_summary = summarize_state()

        return cycle.as_dict()

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



def run_daemon_once(
    *,
    capital: float = 10000.0,
    max_positions: int = 3,
    live: bool = False,
) -> dict[str, Any]:
    daemon = Version9Daemon(
        capital=capital,
        max_positions=max_positions,
        live=live,
    )

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
