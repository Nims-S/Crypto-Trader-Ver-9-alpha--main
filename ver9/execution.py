from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class OrderRequest:
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    price: float | None = None
    order_type: str = "market"
    time_in_force: str = "ioc"
    status: str = "pending"


@dataclass(slots=True)
class FillRecord:
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    fill_price: float
    status: str = "filled"


@dataclass(slots=True)
class ExecutionSummary:
    mode: str
    requested_orders: int
    filled_orders: int
    rejected_orders: int
    fills: list[dict[str, Any]] = field(default_factory=list)
    rejections: list[dict[str, Any]] = field(default_factory=list)
    equity_before: float = 0.0
    equity_after: float = 0.0
    capital_committed: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Broker(Protocol):
    def submit(self, orders: list[OrderRequest]) -> ExecutionSummary: ...


def _stable_ratio(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


class PaperBroker:
    def __init__(self, *, equity: float = 10000.0, fill_threshold: float = 0.35) -> None:
        self.equity = equity
        self.fill_threshold = fill_threshold

    def submit(self, orders: list[OrderRequest]) -> ExecutionSummary:
        fills: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        committed = 0.0

        for order in orders:
            fill_ratio = _stable_ratio(f"{order.strategy_id}:{order.symbol}:{order.side}:{order.quantity}")
            if fill_ratio < self.fill_threshold:
                order.status = "rejected"
                rejections.append(
                    {
                        "strategy_id": order.strategy_id,
                        "symbol": order.symbol,
                        "reason": "fill_simulation_below_threshold",
                        "fill_ratio": round(fill_ratio, 4),
                    }
                )
                continue

            fill_price = order.price if order.price is not None else 100.0 + (fill_ratio * 7.5)
            fills.append(
                {
                    "strategy_id": order.strategy_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": round(order.quantity, 8),
                    "fill_price": round(fill_price, 4),
                }
            )
            committed += float(order.quantity) * float(fill_price)
            order.status = "filled"

        equity_after = max(0.0, self.equity - committed * 0.001)
        return ExecutionSummary(
            mode="paper",
            requested_orders=len(orders),
            filled_orders=len(fills),
            rejected_orders=len(rejections),
            fills=fills,
            rejections=rejections,
            equity_before=self.equity,
            equity_after=round(equity_after, 4),
            capital_committed=round(committed, 4),
        )


class LiveBroker(PaperBroker):
    def submit(self, orders: list[OrderRequest]) -> ExecutionSummary:
        summary = super().submit(orders)
        summary.mode = "live"
        summary.equity_after = max(0.0, summary.equity_after * 0.9995)
        return summary


def build_orders_from_allocations(allocations: list[dict[str, Any]], *, capital: float) -> list[OrderRequest]:
    orders: list[OrderRequest] = []
    for allocation in allocations:
        pct = float(allocation.get("allocation_pct") or 0.0)
        if pct <= 0:
            continue
        order_capital = capital * pct
        symbol = str(allocation.get("symbol") or "")
        strategy_id = str(allocation.get("strategy_id") or "")
        family = str(allocation.get("family") or "")
        side = "buy" if family in {"mean_reversion", "volatility_compression"} else "buy"
        quantity = max(0.0, order_capital / 100.0)
        orders.append(
            OrderRequest(
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                quantity=round(quantity, 8),
                price=100.0 + (_stable_ratio(strategy_id + symbol) * 9.0),
            )
        )
    return orders


def execute_allocations(allocations: list[dict[str, Any]], *, capital: float, live: bool = False) -> ExecutionSummary:
    broker: Broker = LiveBroker(equity=capital) if live else PaperBroker(equity=capital)
    orders = build_orders_from_allocations(allocations, capital=capital)
    return broker.submit(orders)
