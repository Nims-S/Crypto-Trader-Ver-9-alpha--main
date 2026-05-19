from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from ver9.runtime.reconciliation.reconciliation_engine import (
    RuntimeReconciliationEngine,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReconciliationSchedulerConfig:
    interval_seconds: int = 30
    halt_on_divergence: bool = True


class ReconciliationScheduler:
    """
    Periodic reconciliation runtime loop.

    Responsibilities:
    - periodic reconciliation
    - exchange/runtime drift detection
    - forced runtime halts
    - automatic correction hooks
    """

    def __init__(
        self,
        engine: RuntimeReconciliationEngine,
        fetch_local_state: Callable[[], Awaitable[dict]],
        fetch_exchange_state: Callable[[], Awaitable[dict]],
        correction_handler: Callable[[dict], Awaitable[None]],
        halt_handler: Callable[[str], Awaitable[None]],
        config: ReconciliationSchedulerConfig | None = None,
    ) -> None:
        self.engine = engine
        self.fetch_local_state = fetch_local_state
        self.fetch_exchange_state = fetch_exchange_state
        self.correction_handler = correction_handler
        self.halt_handler = halt_handler
        self.config = config or ReconciliationSchedulerConfig()

        self._running = False

    async def start(self) -> None:
        self._running = True

        while self._running:
            try:
                await self._run_cycle()
            except Exception:
                logger.exception("Reconciliation scheduler failure")

            await asyncio.sleep(self.config.interval_seconds)

    async def stop(self) -> None:
        self._running = False

    async def _run_cycle(self) -> None:
        local_state = await self.fetch_local_state()
        exchange_state = await self.fetch_exchange_state()

        order_diff = self.engine.reconcile_orders(
            local_state.get("orders", {}),
            exchange_state.get("orders", {}),
        )

        position_diff = self.engine.reconcile_positions(
            local_state.get("positions", {}),
            exchange_state.get("positions", {}),
        )

        balance_diff = self.engine.reconcile_balances(
            local_state.get("balances", {}),
            exchange_state.get("balances", {}),
        )

        divergence_score = (
            len(order_diff.missing_orders)
            + len(position_diff.stale_positions)
            + len(balance_diff.balance_mismatches)
        )

        if divergence_score > 0:
            logger.warning(
                "Detected reconciliation divergence score=%s",
                divergence_score,
            )

            await self.correction_handler(
                {
                    "orders": order_diff,
                    "positions": position_diff,
                    "balances": balance_diff,
                }
            )

        if divergence_score >= 5 and self.config.halt_on_divergence:
            await self.halt_handler(
                f"reconciliation divergence score={divergence_score}"
            )
