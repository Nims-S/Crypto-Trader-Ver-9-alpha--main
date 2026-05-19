from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from ver9.runtime.recovery.persistent_event_log import PersistentEventLog
from ver9.runtime.recovery.recovery_coordinator import (
    RuntimeRecoveryCoordinator,
)
from ver9.runtime.reconciliation.reconciliation_scheduler import (
    ReconciliationScheduler,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LiveRuntimeState:
    recovered: bool = False
    active: bool = False
    replayed_events: int = 0


class LiveRuntimeOrchestrator:
    """
    Unified live runtime orchestration.

    Responsibilities:
    - runtime startup sequencing
    - replay recovery bootstrap
    - exchange runtime coordination
    - reconciliation scheduling
    - event persistence
    - graceful shutdown
    """

    def __init__(
        self,
        exchange_runtime,
        reconciliation_scheduler: ReconciliationScheduler,
        recovery_coordinator: RuntimeRecoveryCoordinator,
        event_log: PersistentEventLog,
    ) -> None:
        self.exchange_runtime = exchange_runtime
        self.reconciliation_scheduler = reconciliation_scheduler
        self.recovery_coordinator = recovery_coordinator
        self.event_log = event_log

        self.state = LiveRuntimeState()

        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        logger.info("Starting live runtime orchestrator")

        recovery = self.recovery_coordinator.recover()

        self.state.recovered = True
        self.state.replayed_events = recovery.replayed_event_count

        logger.info(
            "Recovered runtime state replayed_events=%s",
            recovery.replayed_event_count,
        )

        self._tasks.append(asyncio.create_task(self.exchange_runtime.start()))
        self._tasks.append(
            asyncio.create_task(self.reconciliation_scheduler.start())
        )

        self.state.active = True

    async def stop(self) -> None:
        logger.info("Stopping live runtime orchestrator")

        self.state.active = False

        await self.exchange_runtime.stop()
        await self.reconciliation_scheduler.stop()

        for task in self._tasks:
            task.cancel()

    async def handle_runtime_event(self, event: dict) -> None:
        self.event_log.append(event)
