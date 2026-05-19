from __future__ import annotations

import logging

from ver9.execution.exchange_adapter import ExchangeExecutionAdapter
from ver9.execution.execution_journal import ExecutionJournal
from ver9.execution.fill_reconciliation import FillReconciliationEngine
from ver9.execution.order_model import ExecutionOrder, OrderStatus
from ver9.execution.order_state_machine import OrderStateMachine
from ver9.execution.retry_policy import ExecutionRetryPolicy

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Core execution orchestration layer.

    Responsibilities:
    - order lifecycle management
    - exchange execution routing
    - execution journaling
    - retry supervision
    - fill reconciliation
    - cancel/replace orchestration
    """

    def __init__(
        self,
        exchange_adapter: ExchangeExecutionAdapter,
        retry_policy: ExecutionRetryPolicy,
        execution_journal: ExecutionJournal,
    ) -> None:
        self.exchange_adapter = exchange_adapter
        self.retry_policy = retry_policy
        self.execution_journal = execution_journal

        self.state_machine = OrderStateMachine()
        self.fill_engine = FillReconciliationEngine()

    async def submit_order(self, order: ExecutionOrder) -> ExecutionOrder:
        self.state_machine.transition(order, OrderStatus.SUBMITTED)

        response = await self.retry_policy.execute(
            self.exchange_adapter.submit_order,
            order,
        )

        order.exchange_order_id = response.get("exchange_order_id")

        self.state_machine.transition(order, OrderStatus.ACKNOWLEDGED)

        self.execution_journal.append_order(order)

        return order

    async def cancel_order(self, order: ExecutionOrder) -> ExecutionOrder:
        self.state_machine.transition(order, OrderStatus.CANCEL_PENDING)

        await self.retry_policy.execute(
            self.exchange_adapter.cancel_order,
            order,
        )

        self.state_machine.transition(order, OrderStatus.CANCELLED)

        self.execution_journal.append_order(order)

        return order

    async def replace_order(
        self,
        order: ExecutionOrder,
        new_quantity: float,
        new_price: float,
    ) -> ExecutionOrder:
        await self.retry_policy.execute(
            self.exchange_adapter.replace_order,
            order,
            new_quantity,
            new_price,
        )

        order.quantity = new_quantity
        order.price = new_price

        self.execution_journal.append_order(order)

        return order

    async def apply_fill(
        self,
        order: ExecutionOrder,
        fill_quantity: float,
        fill_price: float,
    ) -> ExecutionOrder:
        self.fill_engine.apply_fill(
            order,
            fill_quantity,
            fill_price,
        )

        self.execution_journal.append_fill(
            {
                "client_order_id": order.client_order_id,
                "fill_quantity": fill_quantity,
                "fill_price": fill_price,
                "status": order.status.value,
            }
        )

        return order
