from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import ArtifactRecord


class ArtifactManager:
    def __init__(self, base_dir: str = "artifacts") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, artifact: ArtifactRecord) -> Path:
        path = self.base_dir / f"{artifact.cycle_id}.json"
        payload = asdict(artifact)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load(self, cycle_id: str) -> dict:
        path = self.base_dir / f"{cycle_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))


def build_artifact(
    *,
    cycle_id: str,
    config: dict,
    survivors: list[dict],
    portfolio: list[dict],
    protections: list[dict],
) -> ArtifactRecord:
    return ArtifactRecord(
        cycle_id=cycle_id,
        generated_at=datetime.now(UTC).isoformat(),
        config=config,
        survivors=survivors,
        portfolio=portfolio,
        protections=protections,
    )
