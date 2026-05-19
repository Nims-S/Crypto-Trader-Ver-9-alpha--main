from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReplayableRuntimeState:
    positions: Dict[str, dict] = field(default_factory=dict)
    balances: Dict[str, float] = field(default_factory=dict)
    open_orders: Dict[str, dict] = field(default_factory=dict)
    fills: Dict[str, dict] = field(default_factory=dict)
    runtime_metadata: Dict[str, Any] = field(default_factory=dict)


class RuntimeReplayRecovery:
    """
    Deterministic replay recovery engine.

    Responsibilities:
    - replay runtime event streams
    - rebuild runtime state
    - recover open positions/orders
    - reconstruct balances
    - support crash recovery
    """

    def rebuild_from_events(
        self,
        events: Iterable[dict],
    ) -> ReplayableRuntimeState:
        state = ReplayableRuntimeState()

        for event in events:
            self._apply_event(state, event)

        return state

    def _apply_event(
        self,
        state: ReplayableRuntimeState,
        event: dict,
    ) -> None:
        event_type = event.get("event_type")
        payload = event.get("payload", {})

        if event_type == "BALANCE_UPDATE":
            asset = payload["asset"]
            state.balances[asset] = payload["balance"]
            return

        if event_type == "ORDER_OPENED":
            order_id = payload["order_id"]
            state.open_orders[order_id] = payload
            return

        if event_type == "ORDER_CLOSED":
            order_id = payload["order_id"]
            state.open_orders.pop(order_id, None)
            return

        if event_type == "FILL_RECEIVED":
            fill_id = payload["fill_id"]
            state.fills[fill_id] = payload
            return

        if event_type == "POSITION_UPDATED":
            symbol = payload["symbol"]
            state.positions[symbol] = payload
            return

        logger.debug("Unhandled replay event type=%s", event_type)
