from __future__ import annotations

import logging
from time import time

from ver9.execution.order_model import ExecutionOrder, OrderStatus

logger = logging.getLogger(__name__)


class InvalidOrderTransition(Exception):
    pass


class OrderStateMachine:
    VALID_TRANSITIONS = {
        OrderStatus.CREATED: {
            OrderStatus.SUBMITTED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        },
        OrderStatus.SUBMITTED: {
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        },
        OrderStatus.ACKNOWLEDGED: {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCEL_PENDING,
            OrderStatus.CANCELLED,
        },
        OrderStatus.PARTIALLY_FILLED: {
            OrderStatus.FILLED,
            OrderStatus.CANCEL_PENDING,
            OrderStatus.CANCELLED,
        },
        OrderStatus.CANCEL_PENDING: {
            OrderStatus.CANCELLED,
            OrderStatus.FILLED,
        },
    }

    def transition(
        self,
        order: ExecutionOrder,
        new_status: OrderStatus,
    ) -> None:
        allowed = self.VALID_TRANSITIONS.get(order.status, set())

        if new_status not in allowed:
            raise InvalidOrderTransition(
                f"invalid transition {order.status} -> {new_status}"
            )

        logger.info(
            "Order transition client_order_id=%s %s -> %s",
            order.client_order_id,
            order.status,
            new_status,
        )

        order.status = new_status
        order.updated_ts = time()
