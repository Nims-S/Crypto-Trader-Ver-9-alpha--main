from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .models import RuntimeEvent


DispatchHandler = Callable[[RuntimeEvent], None]


class EventDispatcher:
    def __init__(self) -> None:
        self.mapping: dict[
            str,
            list[DispatchHandler],
        ] = defaultdict(list)

    def attach(
        self,
        event_name: str,
        handler: DispatchHandler,
    ) -> None:
        self.mapping[event_name].append(handler)

    def dispatch(
        self,
        event: RuntimeEvent,
    ) -> None:
        callbacks = self.mapping.get(
            event.event_type,
            [],
        )

        for callback in callbacks:
            callback(event)
