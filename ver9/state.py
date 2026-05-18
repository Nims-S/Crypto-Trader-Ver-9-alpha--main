from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_PATH = Path("state") / "ver9_runtime_state.json"
RECOVERY_THRESHOLD = 2
ACTIVE_RECOVERY_THRESHOLD = 2
FAILURE_THRESHOLD = 1
DECAY_PER_INACTIVE_CYCLE = 0.12
DECAY_RECOVERY_PER_ACTIVE_CYCLE = 0.05
RETIREMENT_THRESHOLD = 0.65



def _now() -> str:
    return datetime.now(UTC).isoformat()



def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None



def age_in_days(updated_at: str | None) -> float:
    dt = _parse_dt(updated_at)
    if not dt:
        return 9999.0
    return max(0.0, (datetime.now(UTC) - dt).total_seconds() / 86400.0)



def freshness_multiplier(updated_at: str | None) -> float:
    days_old = age_in_days(updated_at)
    if days_old <= 3:
        return 1.0
    if days_old <= 7:
        return 0.9
    if days_old <= 14:
        return 0.75
    if days_old <= 30:
        return 0.5
    return 0.2



def _default_state() -> dict[str, Any]:
    return {
        "created_at": _now(),
        "updated_at": _now(),
        "cycles": [],
        "executions": [],
        "risk_events": [],
        "quarantined_strategies": [],
        "recovery_events": [],
        "retirement_events": [],
        "strategy_health": {},
    }



def _ensure_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("created_at", _now())
    payload.setdefault("updated_at", _now())
    payload.setdefault("cycles", [])
    payload.setdefault("executions", [])
    payload.setdefault("risk_events", [])
    payload.setdefault("quarantined_strategies", [])
    payload.setdefault("recovery_events", [])
    payload.setdefault("retirement_events", [])
    payload.setdefault("strategy_health", {})
    return payload



def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state()
    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime state must be a JSON object")
    return _ensure_defaults(payload)



def save_state(state: dict[str, Any]) -> Path:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["updated_at"] = _now()
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return STATE_PATH



def _health_entry(state: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    health = state.setdefault("strategy_health", {})
    if not isinstance(health, dict):
        health = {}
        state["strategy_health"] = health
    entry = health.get(strategy_id)
    if not isinstance(entry, dict):
        entry = {
            "strategy_id": strategy_id,
            "status": "active",
            "approved_streak": 0,
            "failure_streak": 0,
            "recovery_streak": 0,
            "inactive_cycles": 0,
            "decay_score": 0.0,
            "retired": False,
            "retirement_reason": "",
            "quarantine_reason": "",
            "events": [],
            "last_updated": _now(),
        }
        health[strategy_id] = entry
    else:
        entry.setdefault("strategy_id", strategy_id)
        entry.setdefault("status", "active")
        entry.setdefault("approved_streak", 0)
        entry.setdefault("failure_streak", 0)
        entry.setdefault("recovery_streak", 0)
        entry.setdefault("inactive_cycles", 0)
        entry.setdefault("decay_score", 0.0)
        entry.setdefault("retired", False)
        entry.setdefault("retirement_reason", "")
        entry.setdefault("quarantine_reason", "")
        entry.setdefault("events", [])
        entry.setdefault("last_updated", _now())
    return entry



def _append_list(state: dict[str, Any], key: str, record: dict[str, Any]) -> None:
    items = state.setdefault(key, [])
    if not isinstance(items, list):
        items = []
        state[key] = items
    items.append(record)



def _remove_quarantine_record(state: dict[str, Any], strategy_id: str) -> None:
    items = state.get("quarantined_strategies") or []
    if not isinstance(items, list):
        state["quarantined_strategies"] = []
        return
    state["quarantined_strategies"] = [item for item in items if not (isinstance(item, dict) and item.get("strategy_id") == strategy_id)]



def _sync_registry_status(strategy_id: str, payload: dict[str, Any]) -> None:
    try:
        from .registry import upsert_candidate
    except Exception:
        return
    try:
        upsert_candidate({"strategy_id": strategy_id, **payload})
    except Exception:
        return



def is_quarantined(strategy_id: str) -> bool:
    state = load_state()
    entry = _health_entry(state, strategy_id)
    return str(entry.get("status") or "") == "quarantined"



def quarantine_strategy(strategy_id: str, reason: str = "manual") -> dict[str, Any]:
    return record_strategy_event(strategy_id, approved=False, reason=reason)



def recover_strategy(strategy_id: str, reason: str = "recovery") -> dict[str, Any]:
    return record_strategy_event(strategy_id, approved=True, reason=reason)



def retire_strategy(strategy_id: str, reason: str = "inactive_decay") -> dict[str, Any]:
    state = load_state()
    entry = _health_entry(state, strategy_id)
    entry["retired"] = True
    entry["status"] = "retired"
    entry["retirement_reason"] = reason
    entry["decay_score"] = max(float(entry.get("decay_score") or 0.0), RETIREMENT_THRESHOLD)
    entry["last_updated"] = _now()
    _append_list(state, "retirement_events", {"strategy_id": strategy_id, "reason": reason, "timestamp": _now()})
    _sync_registry_status(strategy_id, {"status": "retired", "retired": True, "retirement_reason": reason, "decay_score": round(float(entry["decay_score"]), 4)})
    save_state(state)
    return entry



def apply_rolling_decay(active_strategy_ids: set[str] | list[str] | None = None) -> dict[str, Any]:
    state = load_state()
    active = {str(item) for item in (active_strategy_ids or []) if str(item)}
    health = state.get("strategy_health") or {}
    if not isinstance(health, dict):
        return state

    changed = False
    for strategy_id, entry in list(health.items()):
        if not isinstance(entry, dict):
            continue
        entry = _health_entry(state, strategy_id)
        if strategy_id in active:
            entry["inactive_cycles"] = 0
            entry["decay_score"] = max(0.0, float(entry.get("decay_score") or 0.0) - DECAY_RECOVERY_PER_ACTIVE_CYCLE)
            if entry.get("retired") and entry["decay_score"] < RETIREMENT_THRESHOLD * 0.8:
                entry["retired"] = False
                entry["retirement_reason"] = ""
            if entry.get("status") == "retired" and not entry.get("retired"):
                entry["status"] = "active"
            changed = True
        else:
            entry["inactive_cycles"] = int(entry.get("inactive_cycles") or 0) + 1
            entry["decay_score"] = min(1.0, float(entry.get("decay_score") or 0.0) + DECAY_PER_INACTIVE_CYCLE)
            if entry["decay_score"] >= RETIREMENT_THRESHOLD and not entry.get("retired"):
                entry["retired"] = True
                entry["status"] = "retired"
                entry["retirement_reason"] = "inactive_decay"
                _append_list(state, "retirement_events", {"strategy_id": strategy_id, "reason": "inactive_decay", "timestamp": _now()})
                _sync_registry_status(strategy_id, {"status": "retired", "retired": True, "retirement_reason": "inactive_decay", "decay_score": round(float(entry["decay_score"]), 4)})
                changed = True
        entry["last_updated"] = _now()
        health[strategy_id] = entry

    state["strategy_health"] = health
    if changed:
        save_state(state)
    return state



def record_strategy_event(strategy_id: str, *, approved: bool, reason: str) -> dict[str, Any]:
    state = load_state()
    entry = _health_entry(state, strategy_id)
    current_status = str(entry.get("status") or "active")

    if approved:
        entry["approved_streak"] = int(entry.get("approved_streak") or 0) + 1
        entry["failure_streak"] = 0
        entry["retired"] = False
        entry["retirement_reason"] = ""
        if current_status == "quarantined":
            entry["recovery_streak"] = int(entry.get("recovery_streak") or 0) + 1
            if entry["recovery_streak"] >= RECOVERY_THRESHOLD:
                entry["status"] = "probationary"
                entry["quarantine_reason"] = ""
                entry["recovery_streak"] = 0
                _append_list(state, "recovery_events", {"strategy_id": strategy_id, "reason": "recovered_from_quarantine", "timestamp": _now()})
        elif current_status == "probationary":
            entry["recovery_streak"] = int(entry.get("recovery_streak") or 0) + 1
            if entry["recovery_streak"] >= ACTIVE_RECOVERY_THRESHOLD:
                entry["status"] = "active"
                entry["recovery_streak"] = 0
                entry["quarantine_reason"] = ""
                _remove_quarantine_record(state, strategy_id)
                _append_list(state, "recovery_events", {"strategy_id": strategy_id, "reason": "promoted_to_active", "timestamp": _now()})
        else:
            entry["recovery_streak"] = 0
    else:
        entry["approved_streak"] = 0
        entry["failure_streak"] = int(entry.get("failure_streak") or 0) + 1
        entry["recovery_streak"] = 0
        entry["quarantine_reason"] = reason
        entry["status"] = "quarantined"
        if entry["failure_streak"] >= FAILURE_THRESHOLD:
            _append_list(state, "quarantined_strategies", {"strategy_id": strategy_id, "reason": reason, "timestamp": _now()})

    entry["events"] = list(entry.get("events") or []) + [{"approved": approved, "reason": reason, "timestamp": _now()}]
    entry["last_updated"] = _now()
    state["strategy_health"][strategy_id] = entry
    _sync_registry_status(strategy_id, {"status": entry.get("status"), "retired": bool(entry.get("retired")), "retirement_reason": entry.get("retirement_reason", ""), "quarantine_reason": entry.get("quarantine_reason", ""), "decay_score": round(float(entry.get("decay_score") or 0.0), 4)})
    save_state(state)
    return entry



def summarize_state() -> dict[str, Any]:
    state = load_state()
    health = state.get("strategy_health") or {}
    status_counts: dict[str, int] = {}
    if isinstance(health, dict):
        for value in health.values():
            if isinstance(value, dict):
                status = str(value.get("status") or "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "path": str(STATE_PATH),
        "cycle_count": len(state.get("cycles") or []),
        "execution_count": len(state.get("executions") or []),
        "risk_event_count": len(state.get("risk_events") or []),
        "quarantined_count": len(state.get("quarantined_strategies") or []),
        "recovery_count": len(state.get("recovery_events") or []),
        "retirement_count": len(state.get("retirement_events") or []),
        "strategy_status_counts": status_counts,
        "latest_cycle": (state.get("cycles") or [{}])[-1] if state.get("cycles") else {},
        "latest_execution": (state.get("executions") or [{}])[-1] if state.get("executions") else {},
    }
