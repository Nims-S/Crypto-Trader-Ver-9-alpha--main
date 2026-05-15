from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("registry") / "ver9_registry.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {
            "created_at": _now(),
            "updated_at": _now(),
            "entries": {},
        }
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry payload must be a JSON object")
    payload.setdefault("created_at", _now())
    payload.setdefault("updated_at", _now())
    payload.setdefault("entries", {})
    return payload


def save_registry(state: dict[str, Any]) -> Path:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["updated_at"] = _now()
    REGISTRY_PATH.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return REGISTRY_PATH


def upsert_candidate(record: dict[str, Any]) -> dict[str, Any]:
    if not record.get("strategy_id"):
        raise ValueError("candidate record must include strategy_id")

    state = load_registry()
    entries = state.setdefault("entries", {})
    current = entries.get(record["strategy_id"], {}) if isinstance(entries, dict) else {}
    merged = {**current, **record, "updated_at": _now()}
    entries[record["strategy_id"]] = merged
    state["entries"] = entries
    save_registry(state)
    return merged


def list_candidates(*, status: str | None = None, family: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
    state = load_registry()
    entries = state.get("entries") or {}
    rows = list(entries.values()) if isinstance(entries, dict) else list(entries)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if status and str(row.get("status") or "").lower() != status.lower():
            continue
        if family and str(row.get("family") or "").lower() != family.lower():
            continue
        if symbol and str(row.get("symbol") or "").upper() != symbol.upper():
            continue
        filtered.append(row)
    return filtered


def get_candidate(strategy_id: str) -> dict[str, Any] | None:
    state = load_registry()
    entries = state.get("entries") or {}
    if not isinstance(entries, dict):
        return None
    value = entries.get(strategy_id)
    return value if isinstance(value, dict) else None


def summarize_registry() -> dict[str, Any]:
    rows = list_candidates()
    by_status: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for row in rows:
        by_status[str(row.get("status") or "unknown")] = by_status.get(str(row.get("status") or "unknown"), 0) + 1
        by_family[str(row.get("family") or "unknown")] = by_family.get(str(row.get("family") or "unknown"), 0) + 1
    return {
        "path": str(REGISTRY_PATH),
        "count": len(rows),
        "by_status": by_status,
        "by_family": by_family,
    }
