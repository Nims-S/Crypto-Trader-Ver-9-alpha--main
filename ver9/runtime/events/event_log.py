from __future__ import annotations

import json
from pathlib import Path

from .models import RuntimeEvent


class EventLog:
    def __init__(
        self,
        *,
        file_path: str = "runtime_event_log.jsonl",
    ) -> None:
        self.file_path = Path(file_path)

    def append(
        self,
        event: RuntimeEvent,
    ) -> None:
        payload = json.dumps(event.to_dict())

        with self.file_path.open(
            mode="a",
            encoding="utf-8",
        ) as handle:
            handle.write(payload + "\n")

    def replay(self) -> list[dict]:
        if not self.file_path.exists():
            return []

        rows: list[dict] = []

        with self.file_path.open(
            mode="r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                rows.append(json.loads(line))

        return rows
