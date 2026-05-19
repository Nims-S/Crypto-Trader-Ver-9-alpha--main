from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


@dataclass(slots=True)
class ValidationReport:
    valid: bool
    row_count: int
    duplicate_timestamps: int
    missing_values: int
    chronological: bool
    gaps_detected: bool


class DataValidationError(RuntimeError):
    pass


class MarketDataValidator:
    def validate(
        self,
        frame: pd.DataFrame,
    ) -> ValidationReport:
        missing_columns = REQUIRED_COLUMNS - set(frame.columns)

        if missing_columns:
            raise DataValidationError(
                f"missing columns: {sorted(missing_columns)}"
            )

        duplicate_timestamps = int(
            frame["timestamp"].duplicated().sum()
        )

        missing_values = int(frame.isna().sum().sum())

        chronological = bool(
            frame["timestamp"].is_monotonic_increasing
        )

        timestamp_diff = (
            frame["timestamp"]
            .sort_values()
            .diff()
            .dropna()
        )

        gaps_detected = bool(
            len(timestamp_diff.unique()) > 3
        )

        valid = (
            duplicate_timestamps == 0
            and missing_values == 0
            and chronological
        )

        return ValidationReport(
            valid=valid,
            row_count=len(frame),
            duplicate_timestamps=duplicate_timestamps,
            missing_values=missing_values,
            chronological=chronological,
            gaps_detected=gaps_detected,
        )
