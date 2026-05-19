from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from ver9.runtime.recovery.replay_recovery import ReplayableRuntimeState

logger = logging.getLogger(__name__)


class RuntimeCheckpointStore:
    """
    Runtime replay checkpoint persistence.

    Responsibilities:
    - periodic state snapshots
    - replay acceleration
    - deterministic recovery checkpoints
    - snapshot compaction foundation
    """

    def __init__(self, path: str = "runtime_checkpoint.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: ReplayableRuntimeState) -> None:
        payload = asdict(state)

        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def load(self) -> ReplayableRuntimeState | None:
        if not self.path.exists():
            return None

        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return ReplayableRuntimeState(**payload)
