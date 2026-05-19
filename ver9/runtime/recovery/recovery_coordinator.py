from __future__ import annotations

import logging
from dataclasses import dataclass

from ver9.runtime.recovery.checkpoint_store import RuntimeCheckpointStore
from ver9.runtime.recovery.persistent_event_log import PersistentEventLog
from ver9.runtime.recovery.replay_recovery import (
    ReplayableRuntimeState,
    RuntimeReplayRecovery,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RecoveryResult:
    recovered_state: ReplayableRuntimeState
    recovered_from_checkpoint: bool
    replayed_event_count: int


class RuntimeRecoveryCoordinator:
    """
    Deterministic runtime recovery coordinator.

    Responsibilities:
    - checkpoint recovery
    - event replay reconstruction
    - deterministic sequencing
    - rollback foundations
    - replay compaction coordination
    """

    def __init__(
        self,
        checkpoint_store: RuntimeCheckpointStore,
        event_log: PersistentEventLog,
        replay_engine: RuntimeReplayRecovery,
    ) -> None:
        self.checkpoint_store = checkpoint_store
        self.event_log = event_log
        self.replay_engine = replay_engine

    def recover(self) -> RecoveryResult:
        checkpoint = self.checkpoint_store.load()
        replay_events = list(self.event_log.replay())

        replay_events = sorted(
            replay_events,
            key=lambda event: (
                event.get("sequence", 0),
                event.get("timestamp", 0),
            ),
        )

        if checkpoint is not None:
            state = checkpoint
        else:
            state = ReplayableRuntimeState()

        rebuilt = self.replay_engine.rebuild_from_events(replay_events)

        state.positions.update(rebuilt.positions)
        state.balances.update(rebuilt.balances)
        state.open_orders.update(rebuilt.open_orders)
        state.fills.update(rebuilt.fills)

        return RecoveryResult(
            recovered_state=state,
            recovered_from_checkpoint=checkpoint is not None,
            replayed_event_count=len(replay_events),
        )
