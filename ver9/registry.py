from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("registry") / "ver9_registry.json"
REGISTRY_LOCK = threading.RLock()
REGIME_BY_FAMILY = {
    "mean_reversion": "mean_reversion",
    "volatility_compression": "volatility_compression",
    "trend": "trend",
}
REQUIRED_FIELDS = {"strategy_id", "family", "regime", "symbol"}
LEGACY_ID_PATTERNS = [(re.compile(r"(?i)_adaptive_"), "_")]


def _now() -> str:
    return datetime.now(UTC).isoformat()



def _default_state() -> dict[str, Any]:
    return {
        "created_at": _now(),
        "updated_at": _now(),
        "entries": {},
        "quarantined": {},
    }



def _backup_corrupt_registry(raw_text: str, reason: str) -> Path:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup_name = f"{REGISTRY_PATH.stem}.corrupt-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.bak"
    backup_path = REGISTRY_PATH.with_name(backup_name)
    backup_path.write_text(f"# registry recovery backup\n# reason: {reason}\n\n{raw_text}", encoding="utf-8")
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



def _ensure_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("created_at", _now())
    payload.setdefault("updated_at", _now())
    payload.setdefault("entries", {})
    payload.setdefault("quarantined", {})
    if not isinstance(payload.get("entries"), dict):
        payload["entries"] = {}
    if not isinstance(payload.get("quarantined"), dict):
        payload["quarantined"] = {}
    return payload



def _is_valid_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    for field in REQUIRED_FIELDS:
        if not str(record.get(field) or "").strip():
            return False
    return True



def _normalize_strategy_id(strategy_id: str) -> str:
    normalized = str(strategy_id or "")
    for pattern, replacement in LEGACY_ID_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    normalized = normalized.replace("__", "_")
    return normalized



def _normalize_record(strategy_id: str, record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    normalized = dict(record)
    normalized_id = _normalize_strategy_id(str(normalized.get("strategy_id") or strategy_id))
    normalized["strategy_id"] = normalized_id
    family = str(normalized.get("family") or "").lower()
    regime = str(normalized.get("regime") or "").lower()
    if regime == "adaptive" and family in REGIME_BY_FAMILY:
        normalized["regime"] = REGIME_BY_FAMILY[family]
        normalized["legacy_regime"] = regime
    if not normalized.get("status") and normalized.get("validation_passed"):
        normalized["status"] = "validated"
    normalized.setdefault("generation_version", "v9")
    normalized.setdefault("strategy_epoch", 1)
    return normalized_id, normalized



def _quarantine_record(state: dict[str, Any], strategy_id: str, record: Any, reason: str) -> None:
    quarantined = state.setdefault("quarantined", {})
    quarantined[strategy_id] = {
        "strategy_id": strategy_id,
        "reason": reason,
        "record": record,
        "quarantined_at": _now(),
    }



def _migrate_legacy_entries(state: dict[str, Any]) -> bool:
    entries = state.get("entries")
    if not isinstance(entries, dict):
        return False

    changed = False
    for strategy_id, record in list(entries.items()):
        if not _is_valid_record(record):
            _quarantine_record(state, strategy_id, record, "malformed_record")
            del entries[strategy_id]
            changed = True
            continue

        normalized_id, normalized_record = _normalize_record(strategy_id, record)
        if normalized_id != strategy_id or normalized_record != record:
            normalized_record["legacy_strategy_id"] = strategy_id if normalized_id != strategy_id else normalized_record.get("legacy_strategy_id", strategy_id)
            entries.pop(strategy_id, None)
            entries[normalized_id] = normalized_record
            changed = True

    if changed:
        state["entries"] = entries
    return changed



def load_registry() -> dict[str, Any]:
    with REGISTRY_LOCK:
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
                _migrate_legacy_entries(state)
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
        migrated = _migrate_legacy_entries(payload)
        if payload.get("_recovered_trailing_data") or migrated:
            save_registry(payload)
        return payload



def save_registry(state: dict[str, Any]) -> Path:
    with REGISTRY_LOCK:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        state = dict(state)
        state["updated_at"] = _now()
        state = _ensure_defaults(state)
        tmp_path = REGISTRY_PATH.with_name(f"{REGISTRY_PATH.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
        os.replace(tmp_path, REGISTRY_PATH)
        return REGISTRY_PATH



def upsert_candidate(record: dict[str, Any]) -> dict[str, Any]:
    if not record.get("strategy_id"):
        raise ValueError("candidate record must include strategy_id")

    with REGISTRY_LOCK:
        state = load_registry()
        entries = state.setdefault("entries", {})
        current = entries.get(record["strategy_id"], {}) if isinstance(entries, dict) else {}
        normalized_id, normalized_record = _normalize_record(record["strategy_id"], {**current, **record})
        normalized_record["updated_at"] = _now()
        entries.pop(record["strategy_id"], None)
        entries[normalized_id] = normalized_record
        state["entries"] = entries
        save_registry(state)
        return normalized_record



def list_candidates(*, status: str | None = None, family: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
    with REGISTRY_LOCK:
        state = load_registry()
        entries = state.get("entries") or {}
        rows = list(entries.values()) if isinstance(entries, dict) else list(entries)
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if not _is_valid_record(row):
                continue
            _, row = _normalize_record(str(row.get("strategy_id") or ""), row)
            if status and str(row.get("status") or "").lower() != status.lower():
                continue
            if family and str(row.get("family") or "").lower() != family.lower():
                continue
            if symbol and str(row.get("symbol") or "").upper() != symbol.upper():
                continue
            filtered.append(row)
        return filtered



def get_candidate(strategy_id: str) -> dict[str, Any] | None:
    with REGISTRY_LOCK:
        state = load_registry()
        entries = state.get("entries") or {}
        if not isinstance(entries, dict):
            return None
        value = entries.get(strategy_id)
        if not isinstance(value, dict) or not _is_valid_record(value):
            return None
        _, value = _normalize_record(strategy_id, value)
        return value



def summarize_registry() -> dict[str, Any]:
    rows = list_candidates()
    by_status: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for row in rows:
        by_status[str(row.get("status") or "unknown")] = by_status.get(str(row.get("status") or "unknown"), 0) + 1
        by_family[str(row.get("family") or "unknown")] = by_family.get(str(row.get("family") or "unknown"), 0) + 1
    state = load_registry()
    return {
        "path": str(REGISTRY_PATH),
        "count": len(rows),
        "quarantined_count": len(state.get("quarantined") or {}),
        "by_status": by_status,
        "by_family": by_family,
    }
