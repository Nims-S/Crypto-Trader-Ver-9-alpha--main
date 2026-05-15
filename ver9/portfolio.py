from __future__ import annotations

from typing import Any

from .basket_optimizer import BasketOptimizer, build_basket


DEFAULT_MIN_POSITIONS = 2
DEFAULT_MAX_POSITIONS = 3


def allocate(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
    soft_fill: bool = True,
) -> list[dict[str, Any]]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=soft_fill,
    )
    return optimizer.allocate(candidates)


def portfolio_summary(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
    soft_fill: bool = True,
) -> dict[str, Any]:
    basket = build_basket(
        candidates,
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=soft_fill,
    )
    return basket.as_dict()


def strict_portfolio(candidates: list[dict[str, Any]], *, max_positions: int = DEFAULT_MAX_POSITIONS) -> list[dict[str, Any]]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=max_positions,
        soft_fill=False,
    )
    return optimizer.allocate(candidates)


def probationary_portfolio(
    candidates: list[dict[str, Any]],
    *,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    min_positions: int = DEFAULT_MIN_POSITIONS,
) -> list[dict[str, Any]]:
    optimizer = BasketOptimizer(
        max_positions=max_positions,
        min_positions=min_positions,
        soft_fill=True,
    )
    return optimizer.allocate(candidates)
