from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExperimentArtifact:
    artifact_type: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExperimentRecord:
    experiment_id: str
    created_at: str

    strategy_id: str
    strategy_family: str

    symbol: str
    timeframe: str

    dataset_rows: int

    parameters: dict[str, Any]
    metrics: dict[str, Any]

    walkforward_summary: dict[str, Any]

    tags: list[str] = field(default_factory=list)
    notes: str = ""

    artifacts: list[ExperimentArtifact] = field(default_factory=list)


class ExperimentTracker:
    def __init__(
        self,
        *,
        storage_root: str = "experiments",
    ) -> None:
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _serialize(self, value: Any) -> Any:
        if is_dataclass(value):
            return {
                key: self._serialize(val)
                for key, val in asdict(value).items()
            }

        if isinstance(value, dict):
            return {
                str(key): self._serialize(val)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [self._serialize(v) for v in value]

        return value

    def create_experiment(
        self,
        *,
        strategy_id: str,
        strategy_family: str,
        symbol: str,
        timeframe: str,
        dataset_rows: int,
        parameters: dict[str, Any],
        metrics: dict[str, Any],
        walkforward_summary: dict[str, Any],
        tags: list[str] | None = None,
        notes: str = "",
    ) -> ExperimentRecord:
        experiment_id = str(uuid.uuid4())

        return ExperimentRecord(
            experiment_id=experiment_id,
            created_at=datetime.now(UTC).isoformat(),
            strategy_id=strategy_id,
            strategy_family=strategy_family,
            symbol=symbol,
            timeframe=timeframe,
            dataset_rows=dataset_rows,
            parameters=self._serialize(parameters),
            metrics=self._serialize(metrics),
            walkforward_summary=self._serialize(walkforward_summary),
            tags=tags or [],
            notes=notes,
        )

    def save(
        self,
        record: ExperimentRecord,
    ) -> str:
        strategy_dir = (
            self.storage_root
            / record.strategy_family
            / record.strategy_id
        )

        strategy_dir.mkdir(parents=True, exist_ok=True)

        path = strategy_dir / f"{record.experiment_id}.json"

        payload = self._serialize(record)

        tmp_path = path.with_suffix(".tmp")

        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

        tmp_path.replace(path)

        return str(path)

    def load_all(
        self,
        *,
        strategy_id: str | None = None,
    ) -> list[ExperimentRecord]:
        files = list(self.storage_root.rglob("*.json"))

        records: list[ExperimentRecord] = []

        for file_path in files:
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            record = ExperimentRecord(**payload)

            if strategy_id and record.strategy_id != strategy_id:
                continue

            records.append(record)

        records.sort(
            key=lambda record: record.created_at,
            reverse=True,
        )

        return records
