from __future__ import annotations

import logging
from collections import defaultdict
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class RuntimeEventRouter:
    """
    Typed runtime event dispatcher.

    Responsibilities:
    - exchange event routing
    - runtime event fanout
    - event-driven orchestration
    - decoupled runtime consumers
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = (
            defaultdict(list)
        )

    def register(
        self,
        event_type: str,
        handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        self._handlers[event_type].append(handler)

    async def dispatch(self, event: dict) -> None:
        event_type = event.get("event_type", "UNKNOWN")

        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug("No handlers registered for event=%s", event_type)
            return

        for handler in handlers:
            await handler(event)
