from __future__ import annotations

import random
from statistics import mean

from .models import (
    ExecutionMetrics,
    FillStatus,
    SimulatedFill,
    SimulatedOrder,
    SimulationResult,
)


class ExecutionSimulator:
    """
    Execution realism simulator.

    Purpose:
    - inject slippage assumptions
    - simulate latency
    - simulate partial fills
    - estimate execution degradation
    - bridge research/live execution gap
    """

    def __init__(
        self,
        *,
        fee_rate: float = 0.0004,
        base_slippage_pct: float = 0.0008,
        latency_range_ms: tuple[int, int] = (20, 250),
        partial_fill_probability: float = 0.08,
        rejection_probability: float = 0.01,
        seed: int = 42,
    ) -> None:
        self.fee_rate = fee_rate
        self.base_slippage_pct = base_slippage_pct
        self.latency_range_ms = latency_range_ms
        self.partial_fill_probability = partial_fill_probability
        self.rejection_probability = rejection_probability
        self.random = random.Random(seed)

    def _simulate_fill_quantity(
        self,
        requested_quantity: float,
    ) -> tuple[float, str]:
        rejection_roll = self.random.random()

        if rejection_roll < self.rejection_probability:
            return 0.0, FillStatus.REJECTED.value

        partial_roll = self.random.random()

        if partial_roll < self.partial_fill_probability:
            fill_ratio = self.random.uniform(0.3, 0.95)

            return (
                requested_quantity * fill_ratio,
                FillStatus.PARTIAL.value,
            )

        return requested_quantity, FillStatus.FILLED.value

    def _simulate_slippage(
        self,
        confidence: float,
    ) -> float:
        volatility_multiplier = self.random.uniform(0.5, 2.5)

        confidence_penalty = max(
            0.5,
            1.5 - confidence,
        )

        return (
            self.base_slippage_pct
            * volatility_multiplier
            * confidence_penalty
        )

    def execute(
        self,
        orders: list[SimulatedOrder],
    ) -> SimulationResult:
        fills: list[SimulatedFill] = []

        for order in orders:
            filled_quantity, status = (
                self._simulate_fill_quantity(
                    order.requested_quantity
                )
            )

            slippage_pct = self._simulate_slippage(
                order.confidence
            )

            if order.side == "buy":
                executed_price = (
                    order.requested_price
                    * (1.0 + slippage_pct)
                )
            else:
                executed_price = (
                    order.requested_price
                    * (1.0 - slippage_pct)
                )

            latency_ms = self.random.randint(
                self.latency_range_ms[0],
                self.latency_range_ms[1],
            )

            fees_paid = (
                filled_quantity
                * executed_price
                * self.fee_rate
            )

            fills.append(
                SimulatedFill(
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=order.side,
                    requested_quantity=round(
                        order.requested_quantity,
                        8,
                    ),
                    filled_quantity=round(
                        filled_quantity,
                        8,
                    ),
                    requested_price=round(
                        order.requested_price,
                        8,
                    ),
                    executed_price=round(
                        executed_price,
                        8,
                    ),
                    slippage_pct=round(
                        slippage_pct * 100.0,
                        6,
                    ),
                    fees_paid=round(fees_paid, 8),
                    latency_ms=latency_ms,
                    status=status,
                    timestamp=order.timestamp,
                )
            )

        metrics = self._build_metrics(fills)

        return SimulationResult(
            fills=fills,
            metrics=metrics,
        )

    def _build_metrics(
        self,
        fills: list[SimulatedFill],
    ) -> ExecutionMetrics:
        if not fills:
            return ExecutionMetrics()

        filled_orders = sum(
            1
            for fill in fills
            if fill.status == FillStatus.FILLED.value
        )

        partial_fills = sum(
            1
            for fill in fills
            if fill.status == FillStatus.PARTIAL.value
        )

        rejected_orders = sum(
            1
            for fill in fills
            if fill.status == FillStatus.REJECTED.value
        )

        return ExecutionMetrics(
            total_orders=len(fills),
            filled_orders=filled_orders,
            rejected_orders=rejected_orders,
            partial_fills=partial_fills,
            average_slippage_pct=round(
                mean(fill.slippage_pct for fill in fills),
                6,
            ),
            average_latency_ms=round(
                mean(fill.latency_ms for fill in fills),
                4,
            ),
            total_fees_paid=round(
                sum(fill.fees_paid for fill in fills),
                8,
            ),
            fill_rate=round(
                (filled_orders + partial_fills)
                / len(fills),
                6,
            ),
        )
