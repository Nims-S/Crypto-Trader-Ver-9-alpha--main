from __future__ import annotations

from typing import Any

VALID_TRANSITIONS = {
    "candidate": {"validated", "quarantined"},
    "validated": {"probationary", "quarantined"},
    "probationary": {"deployable", "quarantined"},
    "deployable": {"live", "quarantined"},
    "live": {"quarantined"},
    "quarantined": {"validated"},
}

MIN_VALIDATION_SCORE = 0.55
MIN_ROBUSTNESS_VALIDATED = 0.75
MIN_ROBUSTNESS_PROBATIONARY = 0.82
MIN_ROBUSTNESS_DEPLOYABLE = 0.90
MIN_PROFIT_FACTOR_VALIDATED = 1.8
MIN_PROFIT_FACTOR_PROBATIONARY = 1.9
MIN_PROFIT_FACTOR_DEPLOYABLE = 2.2
MAX_DRAWDOWN_VALIDATED = -10.0
MAX_DRAWDOWN_PROBATIONARY = -8.5
MAX_DRAWDOWN_DEPLOYABLE = -6.0
MIN_BASKET_DIVERSITY = 1.0
MIN_BASKET_DIVERSITY_DEPLOYABLE = 1.15


def normalize_status(status: str) -> str:
    return status.strip().lower()


class LifecycleError(RuntimeError):
    pass


def transition(record: dict[str, Any], target_status: str) -> dict[str, Any]:
    current = normalize_status(str(record.get("status") or "candidate"))
    target = normalize_status(target_status)

    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise LifecycleError(f"invalid transition: {current} -> {target}")

    updated = dict(record)
    updated["status"] = target
    return updated


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def _symbol_root(symbol: str) -> str:
    symbol = str(symbol or "").upper()
    return symbol.split("/")[0] if symbol else "UNKNOWN"



def _basket_context(record: dict[str, Any], basket_context: dict[str, Any] | None) -> dict[str, Any]:
    context = dict(basket_context or {})
    context.setdefault("selected_count", _as_int(context.get("selected_count"), 0))
    context.setdefault("max_positions", _as_int(context.get("max_positions"), 0))
    context.setdefault("diversity_score", _as_float(context.get("diversity_score"), 0.0))
    context.setdefault("symbol_counts", context.get("symbol_counts") or {})
    context.setdefault("family_counts", context.get("family_counts") or {})
    context.setdefault("regime_counts", context.get("regime_counts") or {})
    context["candidate_symbol_root"] = _symbol_root(str(record.get("symbol") or ""))
    context["candidate_family"] = str(record.get("family") or "unknown").lower()
    context["candidate_regime"] = str(record.get("regime") or "adaptive").lower()
    return context



def _basket_novelty_score(record: dict[str, Any], basket_context: dict[str, Any] | None = None) -> float:
    context = _basket_context(record, basket_context)
    selected_symbols = {str(key).upper() for key in (context.get("symbol_counts") or {}).keys()}
    selected_families = {str(key).lower() for key in (context.get("family_counts") or {}).keys()}
    selected_regimes = {str(key).lower() for key in (context.get("regime_counts") or {}).keys()}

    novelty = 0.0
    if context["candidate_symbol_root"] not in selected_symbols:
        novelty += 0.4
    if context["candidate_family"] not in selected_families:
        novelty += 0.2
    if context["candidate_regime"] not in selected_regimes:
        novelty += 0.1
    if context["diversity_score"] >= MIN_BASKET_DIVERSITY:
        novelty += 0.1
    return round(novelty, 4)



def can_enter_probationary_basket(record: dict[str, Any], basket_context: dict[str, Any] | None = None) -> bool:
    if normalize_status(str(record.get("status") or "candidate")) == "quarantined":
        return False

    robustness = _as_float(record.get("robustness_score"), 0.0)
    profit_factor = _as_float(record.get("profit_factor"), 0.0)
    drawdown = _as_float(record.get("max_drawdown_pct"), 0.0)
    validation_score = _as_float(record.get("validation_score"), 0.0)
    validation_passed = bool(record.get("validation_passed"))

    if not validation_passed and validation_score < MIN_VALIDATION_SCORE:
        return False
    if robustness < MIN_ROBUSTNESS_PROBATIONARY:
        return False
    if profit_factor < MIN_PROFIT_FACTOR_PROBATIONARY:
        return False
    if drawdown < MAX_DRAWDOWN_PROBATIONARY:
        return False

    context = _basket_context(record, basket_context)
    if context["selected_count"] == 0:
        return True

    return _basket_novelty_score(record, context) >= 0.3



def can_enter_deployable_basket(record: dict[str, Any], basket_context: dict[str, Any] | None = None) -> bool:
    robustness = _as_float(record.get("robustness_score"), 0.0)
    profit_factor = _as_float(record.get("profit_factor"), 0.0)
    drawdown = _as_float(record.get("max_drawdown_pct"), 0.0)
    validation_score = _as_float(record.get("validation_score"), 0.0)
    validation_passed = bool(record.get("validation_passed"))

    if not validation_passed and validation_score < MIN_VALIDATION_SCORE:
        return False
    if robustness < MIN_ROBUSTNESS_DEPLOYABLE:
        return False
    if profit_factor < MIN_PROFIT_FACTOR_DEPLOYABLE:
        return False
    if drawdown < MAX_DRAWDOWN_DEPLOYABLE:
        return False

    context = _basket_context(record, basket_context)
    if context["selected_count"] == 0:
        return True

    return (
        _basket_novelty_score(record, context) >= 0.45
        and context["diversity_score"] >= MIN_BASKET_DIVERSITY_DEPLOYABLE
    )



def auto_promote(record: dict[str, Any], basket_context: dict[str, Any] | None = None) -> dict[str, Any]:
    updated = dict(record)
    current_status = normalize_status(str(updated.get("status") or "candidate"))
    if current_status in {"live", "quarantined"}:
        return updated

    robustness = _as_float(updated.get("robustness_score"), 0.0)
    profit_factor = _as_float(updated.get("profit_factor"), 0.0)
    drawdown = _as_float(updated.get("max_drawdown_pct"), 0.0)
    validation_score = _as_float(updated.get("validation_score"), 0.0)
    validation_passed = bool(updated.get("validation_passed"))

    basket_ready = _basket_context(updated, basket_context)

    if validation_passed and validation_score >= MIN_VALIDATION_SCORE and robustness >= MIN_ROBUSTNESS_VALIDATED and profit_factor >= MIN_PROFIT_FACTOR_VALIDATED and drawdown >= MAX_DRAWDOWN_VALIDATED:
        updated["status"] = "validated"

    if can_enter_probationary_basket(updated, basket_ready):
        updated["status"] = "probationary"

    if can_enter_deployable_basket(updated, basket_ready):
        updated["status"] = "deployable"

    return updated
