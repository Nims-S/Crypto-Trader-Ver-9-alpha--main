from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(slots=True)
class FeatureSetMetadata:
    feature_set_id: str
    strategy_family: str
    symbol: str
    timeframe: str
    row_count: int
    feature_columns: list[str]
    dataset_hash: str
    feature_hash: str
    version: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StoredFeatureSet:
    metadata: FeatureSetMetadata
    parquet_path: str


class FeatureStore:
    def __init__(
        self,
        *,
        storage_root: str = "feature_store",
    ) -> None:
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _hash_frame(
        self,
        frame: pd.DataFrame,
    ) -> str:
        payload = pd.util.hash_pandas_object(
            frame,
            index=True,
        ).values.tobytes()

        return hashlib.sha256(payload).hexdigest()

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

    def save_feature_set(
        self,
        *,
        strategy_family: str,
        symbol: str,
        timeframe: str,
        frame: pd.DataFrame,
        feature_columns: list[str],
        version: str = "v1",
        tags: list[str] | None = None,
    ) -> StoredFeatureSet:
        working = frame.copy()

        dataset_hash = self._hash_frame(
            working[["timestamp", "open", "high", "low", "close", "volume"]]
        )

        feature_hash = self._hash_frame(
            working[feature_columns]
        )

        feature_set_id = hashlib.sha256(
            f"{strategy_family}:{symbol}:{timeframe}:{feature_hash}".encode()
        ).hexdigest()[:16]

        storage_dir = (
            self.storage_root
            / strategy_family
            / symbol.replace("/", "_").lower()
            / timeframe
        )

        storage_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = storage_dir / f"{feature_set_id}.parquet"
        metadata_path = storage_dir / f"{feature_set_id}.json"

        working.to_parquet(parquet_path, index=False)

        metadata = FeatureSetMetadata(
            feature_set_id=feature_set_id,
            strategy_family=strategy_family,
            symbol=symbol,
            timeframe=timeframe,
            row_count=len(working),
            feature_columns=feature_columns,
            dataset_hash=dataset_hash,
            feature_hash=feature_hash,
            version=version,
            tags=tags or [],
        )

        tmp_metadata = metadata_path.with_suffix(".tmp")

        with tmp_metadata.open("w", encoding="utf-8") as handle:
            json.dump(
                self._serialize(metadata),
                handle,
                indent=2,
                sort_keys=True,
            )

        tmp_metadata.replace(metadata_path)

        return StoredFeatureSet(
            metadata=metadata,
            parquet_path=str(parquet_path),
        )

    def load_feature_set(
        self,
        parquet_path: str,
    ) -> pd.DataFrame:
        return pd.read_parquet(parquet_path)
