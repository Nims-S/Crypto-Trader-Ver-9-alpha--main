from __future__ import annotations

from abc import ABC, abstractmethod

from ver9.execution.order_model import ExecutionOrder


class ExchangeExecutionAdapter(ABC):
    """
    Canonical execution adapter interface.

    Responsibilities:
    - exchange order submission
    - order cancellation
    - order replacement
    - order queries
    - execution abstraction
    """

    @abstractmethod
    async def submit_order(self, order: ExecutionOrder) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, order: ExecutionOrder) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def replace_order(
        self,
        order: ExecutionOrder,
        new_quantity: float,
        new_price: float,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def fetch_order(self, order: ExecutionOrder) -> dict:
        raise NotImplementedError
