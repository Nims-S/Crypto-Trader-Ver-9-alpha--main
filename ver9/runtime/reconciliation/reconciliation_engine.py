from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReconciliationDiff:
    missing_orders: List[str] = field(default_factory=list)
    stale_positions: List[str] = field(default_factory=list)
    balance_mismatches: Dict[str, float] = field(default_factory=dict)
    fill_mismatches: List[str] = field(default_factory=list)


class RuntimeReconciliationEngine:
    """
    Exchange truth reconciliation layer.

    Responsibilities:
    - reconcile local/runtime orders
    - reconcile fills
    - reconcile balances
    - reconcile positions
    - detect runtime drift
    """

    def reconcile_orders(
        self,
        local_orders: Dict[str, dict],
        exchange_orders: Dict[str, dict],
    ) -> ReconciliationDiff:
        diff = ReconciliationDiff()

        for order_id in local_orders:
            if order_id not in exchange_orders:
                diff.missing_orders.append(order_id)

        return diff

    def reconcile_positions(
        self,
        local_positions: Dict[str, dict],
        exchange_positions: Dict[str, dict],
    ) -> ReconciliationDiff:
        diff = ReconciliationDiff()

        for symbol, local_position in local_positions.items():
            exchange_position = exchange_positions.get(symbol)

            if exchange_position is None:
                diff.stale_positions.append(symbol)
                continue

            local_qty = float(local_position.get("quantity", 0.0))
            exchange_qty = float(exchange_position.get("quantity", 0.0))

            if abs(local_qty - exchange_qty) > 1e-9:
                diff.stale_positions.append(symbol)

        return diff

    def reconcile_balances(
        self,
        local_balances: Dict[str, float],
        exchange_balances: Dict[str, float],
    ) -> ReconciliationDiff:
        diff = ReconciliationDiff()

        for asset, local_balance in local_balances.items():
            exchange_balance = exchange_balances.get(asset)

            if exchange_balance is None:
                diff.balance_mismatches[asset] = local_balance
                continue

            if abs(local_balance - exchange_balance) > 1e-6:
                diff.balance_mismatches[asset] = (
                    local_balance - exchange_balance
                )

        return diff

    def reconcile_fills(
        self,
        local_fills: Dict[str, dict],
        exchange_fills: Dict[str, dict],
    ) -> ReconciliationDiff:
        diff = ReconciliationDiff()

        for fill_id in local_fills:
            if fill_id not in exchange_fills:
                diff.fill_mismatches.append(fill_id)

        return diff

    def summarize(self, diff: ReconciliationDiff) -> dict:
        return {
            "missing_orders": len(diff.missing_orders),
            "stale_positions": len(diff.stale_positions),
            "balance_mismatches": len(diff.balance_mismatches),
            "fill_mismatches": len(diff.fill_mismatches),
        }
