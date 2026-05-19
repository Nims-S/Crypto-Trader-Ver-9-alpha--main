from __future__ import annotations

import json
from pathlib import Path

from .state_models import RuntimeSnapshot


class RuntimeStateStore:
    """
    Persistent runtime state storage.

    Purpose:
    - restart recovery
    - runtime persistence
    - state synchronization
    - crash resilience
    """

    def __init__(
        self,
        *,
        storage_root: str = "runtime_state",
    ) -> None:
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        snapshot: RuntimeSnapshot,
    ) -> Path:
        snapshot.refresh()

        path = (
            self.storage_root
            / f"{snapshot.runtime_id}.json"
        )

        temporary_path = path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                snapshot.to_dict(),
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(path)

        return path

    def load(
        self,
        runtime_id: str,
    ) -> RuntimeSnapshot | None:
        path = self.storage_root / f"{runtime_id}.json"

        if not path.exists():
            return None

        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        return RuntimeSnapshot(**payload)
