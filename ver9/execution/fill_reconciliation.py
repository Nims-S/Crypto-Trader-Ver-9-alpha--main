from __future__ import annotations

import logging

from ver9.execution.order_model import ExecutionOrder, OrderStatus

logger = logging.getLogger(__name__)


class FillReconciliationEngine:
    """
    Execution fill reconciliation.

    Responsibilities:
    - partial fill handling
    - fill aggregation
    - execution consistency
    - average fill calculation
    """

    def apply_fill(
        self,
        order: ExecutionOrder,
        fill_quantity: float,
        fill_price: float,
    ) -> None:
        previous_notional = (
            order.filled_quantity * order.average_fill_price
        )

        fill_notional = fill_quantity * fill_price

        order.filled_quantity += fill_quantity

        if order.filled_quantity > 0:
            order.average_fill_price = (
                previous_notional + fill_notional
            ) / order.filled_quantity

        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        logger.info(
            "Applied fill order=%s filled=%s/%s avg_price=%s",
            order.client_order_id,
            order.filled_quantity,
            order.quantity,
            order.average_fill_price,
        )
