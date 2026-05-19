from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ver9.execution.order_model import ExecutionOrder


class ExecutionJournal:
    """
    Durable execution journal.

    Responsibilities:
    - order journaling
    - fill journaling
    - execution persistence
    - recovery source-of-truth
    """

    def __init__(self, path: str = "execution_journal.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_order(self, order: ExecutionOrder) -> None:
        payload = {
            "record_type": "ORDER",
            "payload": asdict(order),
        }

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def append_fill(self, fill: dict) -> None:
        payload = {
            "record_type": "FILL",
            "payload": fill,
        }

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
