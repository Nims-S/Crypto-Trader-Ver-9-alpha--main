from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("registry") / "ver9_registry.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()



def _default_state() -> dict[str, Any]:
    return {
        "created_at": _now(),
        "updated_at": _now(),
        "entries": {},
    }



def _backup_corrupt_registry(raw_text: str, reason: str) -> Path:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup_name = f"{REGISTRY_PATH.stem}.corrupt-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.bak"
    backup_path = REGISTRY_PATH.with_name(backup_name)
    backup_path.write_text(
        f"# registry recovery backup\n# reason: {reason}\n\n{raw_text}",
        encoding="utf-8",
    )
    return backup_path



def _recover_json_payload(raw_text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    try:
        payload, end = decoder.raw_decode(raw_text.lstrip())
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    trailing = raw_text.lstrip()[end:].strip()
    if trailing:
        payload = dict(payload)
        payload["_recovered_trailing_data"] = True
    return payload



def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return _default_state()

    raw_text = REGISTRY_PATH.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        recovered = _recover_json_payload(raw_text)
        if recovered is not None:
            _backup_corrupt_registry(raw_text, f"json_decode_error:{exc}")
            state = _ensure_defaults(recovered)
            save_registry(state)
            return state

        _backup_corrupt_registry(raw_text, f"json_decode_error:{exc}")
        state = _default_state()
        save_registry(state)
        return state

    if not isinstance(payload, dict):
        _backup_corrupt_registry(raw_text, "registry_payload_not_object")
        state = _default_state()
        save_registry(state)
        return state

    payload = _ensure_defaults(payload)
    if payload.get("_recovered_trailing_data"):
        save_registry(payload)
    return payload



def _ensure_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("created_at", _now())
    payload.setdefault("updated_at", _now())
    payload.setdefault("entries", {})
    if not isinstance(payload.get("entries"), dict):
        payload["entries"] = {}
    return payload



def save_registry(state: dict[str, Any]) -> Path:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["updated_at"] = _now()
    state = _ensure_defaults(state)
    tmp_path = REGISTRY_PATH.with_name(f"{REGISTRY_PATH.name}.tmp")
    tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp_path, REGISTRY_PATH)
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