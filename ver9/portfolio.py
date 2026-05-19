from __future__ import annotations

from typing import Any

from .basket_optimizer import BasketOptimizer, build_basket
from .models import AllocationDecision, PortfolioSnapshot


DEFAULT_MIN_POSITIONS = 2
DEFAULT_MAX_POSITIONS = 3


def _allocation_from_dict(allocation: dict[str, Any]) -> AllocationDecision:
    return AllocationDecision(
        strategy_id=str(allocation.get("strategy_id") or ""),
        symbol=str(allocation.get("symbol") or ""),
        weight=float(allocation.get("allocation_pct") or 0.0),
        capital_allocated=float(allocation.get("capital_allocated") or 0.0),
        expected_risk=float(allocation.get("expected_risk") or 0.0),
        covariance_penalty=float(allocation.get("correlation_penalty") or 0.0),
        selection_reason=str(allocation.get("selection_reason") or "optimizer_selected"),
        metadata=dict(allocation),
    )


def allocate(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
    soft_fill: bool = True,
) -> list[AllocationDecision]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=soft_fill,
    )

    allocations = optimizer.allocate(candidates)
    return [_allocation_from_dict(row) for row in allocations]


def portfolio_summary(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
    soft_fill: bool = True,
) -> PortfolioSnapshot:
    basket = build_basket(
        candidates,
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=soft_fill,
    )

    allocations = [_allocation_from_dict(row) for row in basket.selected]

    return PortfolioSnapshot(
        total_capital=float(getattr(basket, "capital", 0.0) or 0.0),
        gross_exposure=float(getattr(basket, "gross_exposure", 0.0) or 0.0),
        net_exposure=float(getattr(basket, "net_exposure", 0.0) or 0.0),
        cash_weight=float(getattr(basket, "cash_weight", 0.0) or 0.0),
        allocations=allocations,
    )


def strict_portfolio(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
) -> list[AllocationDecision]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=max_positions,
        soft_fill=False,
    )

    allocations = optimizer.allocate(candidates)
    return [_allocation_from_dict(row) for row in allocations]


def probationary_portfolio(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
) -> list[AllocationDecision]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=True,
    )

    allocations = optimizer.allocate(candidates)
    return [_allocation_from_dict(row) for row in allocations]
