from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_PATH = Path("state") / "ver9_runtime_state.json"
RECOVERY_THRESHOLD = 2
FAILURE_THRESHOLD = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "created_at": _now(),
        "updated_at": _now(),
        "cycles": [],
        "executions": [],
        "risk_events": [],
        "quarantined_strategies": [],
        "recovery_events": [],
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
        entry.setdefault("quarantine_reason", "")
        entry.setdefault("events", [])
        entry.setdefault("last_updated", _now())
    return entry


def _append_quarantine_record(state: dict[str, Any], strategy_id: str, reason: str) -> None:
    records = state.setdefault("quarantined_strategies", [])
    if not isinstance(records, list):
        records = []
        state["quarantined_strategies"] = records
    if any(isinstance(item, dict) and item.get("strategy_id") == strategy_id for item in records):
        return
    records.append({"strategy_id": strategy_id, "reason": reason, "timestamp": _now()})


def _remove_quarantine_record(state: dict[str, Any], strategy_id: str) -> None:
    records = state.get("quarantined_strategies") or []
    if not isinstance(records, list):
        state["quarantined_strategies"] = []
        return
    state["quarantined_strategies"] = [item for item in records if not (isinstance(item, dict) and item.get("strategy_id") == strategy_id)]


def record_strategy_event(strategy_id: str, *, approved: bool, reason: str) -> dict[str, Any]:
    state = load_state()
    entry = _health_entry(state, strategy_id)

    if approved:
        entry["approved_streak"] = int(entry.get("approved_streak") or 0) + 1
        entry["failure_streak"] = 0

        if str(entry.get("status") or "active") == "quarantined":
            entry["recovery_streak"] = int(entry.get("recovery_streak") or 0) + 1
            if entry["recovery_streak"] >= RECOVERY_THRESHOLD:
                entry["status"] = "probationary"
                entry["quarantine_reason"] = ""
                entry["recovery_streak"] = 0
                state.setdefault("recovery_events", []).append(
                    {"strategy_id": strategy_id, "reason": "recovered_from_quarantine", "timestamp": _now()}
                )
                _remove_quarantine_record(state, strategy_id)
        else:
            entry["recovery_streak"] = 0
            if str(entry.get("status") or "active") not in {"validated", "probationary", "deployable", "live"}:
                entry["status"] = "active"
    else:
        entry["approved_streak"] = 0
        entry["failure_streak"] = int(entry.get("failure_streak") or 0) + 1
        entry["recovery_streak"] = 0
        entry["quarantine_reason"] = reason
        entry["status"] = "quarantined"
        if entry["failure_streak"] >= FAILURE_THRESHOLD:
            _append_quarantine_record(state, strategy_id, reason)

    entry["events"] = list(entry.get("events") or []) + [
        {"approved": approved, "reason": reason, "timestamp": _now()}
    ]
    entry["last_updated"] = _now()
    state["strategy_health"][strategy_id] = entry
    save_state(state)
    return entry


def quarantine_strategy(strategy_id: str, reason: str) -> dict[str, Any]:
    return record_strategy_event(strategy_id, approved=False, reason=reason)


def recover_strategy(strategy_id: str, reason: str = "approved_cycle") -> dict[str, Any]:
    return record_strategy_event(strategy_id, approved=True, reason=reason)


def is_quarantined(strategy_id: str) -> bool:
    state = load_state()
    health = state.get("strategy_health") or {}
    if isinstance(health, dict):
        entry = health.get(strategy_id)
        if isinstance(entry, dict) and str(entry.get("status") or "") == "quarantined":
            return True
    records = state.get("quarantined_strategies") or []
    if isinstance(records, list):
        return any(isinstance(item, dict) and item.get("strategy_id") == strategy_id for item in records)
    return False


def append_cycle(cycle: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    state["cycles"].append(cycle)
    save_state(state)
    return cycle


def append_execution(execution: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    state["executions"].append(execution)
    save_state(state)
    return execution


def append_risk_event(event: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    state["risk_events"].append(event)
    save_state(state)
    return event


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
        "strategy_status_counts": status_counts,
        "latest_cycle": (state.get("cycles") or [{}])[-1] if state.get("cycles") else {},
        "latest_execution": (state.get("executions") or [{}])[-1] if state.get("executions") else {},
    }
