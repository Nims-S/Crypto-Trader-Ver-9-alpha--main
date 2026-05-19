from __future__ import annotations

from .engine import ExecutionSimulator
from .models import SimulatedOrder, SimulatedFill


class OrderRuntime:
    def __init__(
        self,
        simulator: ExecutionSimulator | None = None,
    ) -> None:
        self.simulator = simulator or ExecutionSimulator()
        self.history: list[SimulatedFill] = []

    def process(
        self,
        orders: list[SimulatedOrder],
    ) -> list[SimulatedFill]:
        result = self.simulator.execute(orders)

        for fill in result.fills:
            self.history.append(fill)

        return result.fills
