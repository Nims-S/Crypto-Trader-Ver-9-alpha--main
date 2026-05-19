from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any


def serialize_model(obj: Any) -> Any:
    """Serialize dataclass models into JSON-safe dictionaries."""

    if is_dataclass(obj):
        data = asdict(obj)

        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return data

    if isinstance(obj, list):
        return [serialize_model(item) for item in obj]

    if isinstance(obj, dict):
        return {
            key: serialize_model(value)
            for key, value in obj.items()
        }

    return obj
