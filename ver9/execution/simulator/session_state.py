from __future__ import annotations

from dataclasses import dataclass, field

from .engine import ExecutionSimulator
from .models import SimulatedFill, SimulatedOrder


@dataclass(slots=True)
class SessionPosition:
    asset: str
    quantity: float
    average_price: float


@dataclass(slots=True)
class SessionAccountState:
    total_equity: float
    available_cash: float
    positions: dict[str, SessionPosition] = field(
        default_factory=dict
    )


@dataclass(slots=True)
class SessionStatistics:
    submitted_orders: int = 0
    processed_fills: int = 0
    rejected_orders: int = 0
    cumulative_fees: float = 0.0


class PaperSession:
    """
    Stateful paper trading session wrapper.

    Purpose:
    - maintain simulated account state
    - process execution simulator fills
    - track portfolio equity evolution
    - support runtime lifecycle testing
    - bridge research and deployment behavior
    """

    def __init__(
        self,
        *,
        starting_equity: float = 10000.0,
        simulator: ExecutionSimulator | None = None,
    ) -> None:
        self.simulator = simulator or ExecutionSimulator()

        self.account = SessionAccountState(
            total_equity=starting_equity,
            available_cash=starting_equity,
        )

        self.statistics = SessionStatistics()

        self.execution_history: list[SimulatedFill] = []

    def process_orders(
        self,
        orders: list[SimulatedOrder],
    ) -> list[SimulatedFill]:
        self.statistics.submitted_orders += len(orders)

        simulation = self.simulator.execute(orders)

        for fill in simulation.fills:
            self.execution_history.append(fill)

            if fill.status == "rejected":
                self.statistics.rejected_orders += 1
                continue

            self.statistics.processed_fills += 1
            self.statistics.cumulative_fees += fill.fees_paid

            self._apply_fill(fill)

        return simulation.fills

    def _apply_fill(
        self,
        fill: SimulatedFill,
    ) -> None:
        gross_value = (
            fill.executed_price
            * fill.filled_quantity
        )

        if fill.side == "buy":
            self.account.available_cash -= (
                gross_value + fill.fees_paid
            )

            existing = self.account.positions.get(
                fill.symbol
            )

            if existing:
                total_quantity = (
                    existing.quantity
                    + fill.filled_quantity
                )

                blended_price = (
                    (
                        existing.quantity
                        * existing.average_price
                    )
                    + (
                        fill.filled_quantity
                        * fill.executed_price
                    )
                ) / total_quantity

                existing.quantity = total_quantity
                existing.average_price = blended_price

            else:
                self.account.positions[fill.symbol] = (
                    SessionPosition(
                        asset=fill.symbol,
                        quantity=fill.filled_quantity,
                        average_price=fill.executed_price,
                    )
                )

        else:
            self.account.available_cash += (
                gross_value - fill.fees_paid
            )

            existing = self.account.positions.get(
                fill.symbol
            )

            if existing:
                existing.quantity -= fill.filled_quantity

                if existing.quantity <= 0:
                    del self.account.positions[
                        fill.symbol
                    ]

        self._refresh_equity()

    def _refresh_equity(self) -> None:
        equity = self.account.available_cash

        for position in self.account.positions.values():
            equity += (
                position.quantity
                * position.average_price
            )

        self.account.total_equity = equity
