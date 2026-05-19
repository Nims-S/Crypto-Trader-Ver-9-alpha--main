from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class QueuedEvent:
    event_id: str
    event_type: str
    payload: dict[str, Any]


class EventQueueState:
    def __init__(self) -> None:
        self.items: list[QueuedEvent] = []

    def push(self, event: QueuedEvent) -> None:
        self.items.append(event)

    def pop(self) -> QueuedEvent | None:
        if not self.items:
            return None

        return self.items.pop(0)

    def size(self) -> int:
        return len(self.items)
