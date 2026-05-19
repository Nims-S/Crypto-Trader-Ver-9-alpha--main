from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PersistentEventLogConfig:
    path: str = "runtime_event_log.jsonl"


class PersistentEventLog:
    """
    Durable runtime event log.

    Responsibilities:
    - append-only runtime journaling
    - deterministic replay ordering
    - replay persistence
    - recovery source-of-truth
    """

    def __init__(self, config: PersistentEventLogConfig | None = None) -> None:
        self.config = config or PersistentEventLogConfig()
        self.path = Path(self.config.path)

        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    def replay(self) -> Iterable[dict]:
        if not self.path.exists():
            return []

        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                yield json.loads(line)
