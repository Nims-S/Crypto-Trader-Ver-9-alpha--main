from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .models import RuntimeEvent


MessageHandler = Callable[[RuntimeEvent], None]


class MessageBus:
    def __init__(self) -> None:
        self.subscribers: dict[
            str,
            list[MessageHandler],
        ] = defaultdict(list)

    def subscribe(
        self,
        topic: str,
        handler: MessageHandler,
    ) -> None:
        self.subscribers[topic].append(handler)

    def publish(
        self,
        event: RuntimeEvent,
    ) -> None:
        handlers = self.subscribers.get(
            event.event_type,
            [],
        )

        for handler in handlers:
            handler(event)
