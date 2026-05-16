from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
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
    acceptance_history: list[dict[str, Any]] = field(default_factory=list)
    rejection_telemetry: dict[str, Any] = field(default_factory=dict)
    per_strategy_stats: dict[str, Any] = field(default_factory=dict)
    fill_rate: float = 0.0
    average_slippage_bps: float = 0.0
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



def _slippage_bps(expected_price: float | None, fill_price: float) -> float:
    if expected_price is None or expected_price <= 0:
        return 0.0
    return ((fill_price - expected_price) / expected_price) * 10000.0



def _build_execution_telemetry(
    orders: list[OrderRequest],
    fills: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], float]:
    fill_by_strategy: dict[str, int] = Counter()
    request_by_strategy: dict[str, int] = Counter()
    reject_by_strategy: dict[str, int] = Counter()
    slippage_by_strategy: dict[str, list[float]] = defaultdict(list)
    rejection_reason_counts: Counter[str] = Counter()
    acceptance_history: list[dict[str, Any]] = []

    fills_by_key = {
        (str(item.get("strategy_id") or ""), str(item.get("symbol") or ""), str(item.get("side") or ""), round(float(item.get("quantity") or 0.0), 8)): item
        for item in fills
    }

    rejection_lookup = {
        (str(item.get("strategy_id") or ""), str(item.get("symbol") or ""), item.get("reason")): item
        for item in rejections
    }

    for order in orders:
        strategy_id = order.strategy_id
        request_by_strategy[strategy_id] += 1
        fill_price = None
        accepted = False
        fill_ratio = _stable_ratio(f"{order.strategy_id}:{order.symbol}:{order.side}:{order.quantity}")
        slippage_bps = None
        rejection_reason = None

        fill_key = (strategy_id, order.symbol, order.side, round(float(order.quantity), 8))
        fill = fills_by_key.get(fill_key)
        if fill is not None:
            accepted = True
            fill_price = float(fill.get("fill_price") or 0.0)
            fill_by_strategy[strategy_id] += 1
            slippage_bps = round(_slippage_bps(order.price, fill_price), 4)
            slippage_by_strategy[strategy_id].append(slippage_bps)
        else:
            rejection_reason = next(
                (
                    item.get("reason")
                    for item in rejections
                    if str(item.get("strategy_id") or "") == strategy_id
                    and str(item.get("symbol") or "") == str(order.symbol or "")
                ),
                "unfilled",
            )
            reject_by_strategy[strategy_id] += 1
            rejection_reason_counts[str(rejection_reason or "unfilled")] += 1

        acceptance_history.append(
            {
                "strategy_id": strategy_id,
                "symbol": order.symbol,
                "side": order.side,
                "requested_quantity": round(float(order.quantity), 8),
                "expected_price": round(float(order.price or 0.0), 4) if order.price is not None else None,
                "fill_price": round(float(fill_price or 0.0), 4) if fill_price is not None else None,
                "accepted": accepted,
                "fill_ratio": round(fill_ratio, 4),
                "slippage_bps": slippage_bps,
                "rejection_reason": rejection_reason,
            }
        )

    per_strategy_stats: dict[str, Any] = {}
    for strategy_id in sorted(set(request_by_strategy) | set(fill_by_strategy) | set(reject_by_strategy)):
        fills_count = fill_by_strategy.get(strategy_id, 0)
        requests_count = request_by_strategy.get(strategy_id, 0)
        rejects_count = reject_by_strategy.get(strategy_id, 0)
        slippage_values = slippage_by_strategy.get(strategy_id, [])
        per_strategy_stats[strategy_id] = {
            "requested_orders": requests_count,
            "filled_orders": fills_count,
            "rejected_orders": rejects_count,
            "fill_rate": round((fills_count / requests_count) if requests_count else 0.0, 6),
            "average_slippage_bps": round((sum(slippage_values) / len(slippage_values)) if slippage_values else 0.0, 4),
        }

    rejection_telemetry = {
        "reasons": dict(rejection_reason_counts),
        "total_rejections": len(rejections),
        "unique_strategies_rejected": len(reject_by_strategy),
    }

    fill_rate = round((len(fills) / len(orders)) if orders else 0.0, 6)
    all_slippage = [value for values in slippage_by_strategy.values() for value in values]
    average_slippage_bps = round((sum(all_slippage) / len(all_slippage)) if all_slippage else 0.0, 4)
    return acceptance_history, rejection_telemetry, per_strategy_stats, fill_rate, average_slippage_bps


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

        acceptance_history, rejection_telemetry, per_strategy_stats, fill_rate, avg_slippage_bps = _build_execution_telemetry(
            orders,
            fills,
            rejections,
        )

        equity_after = max(0.0, self.equity - committed * 0.001)
        return ExecutionSummary(
            mode="paper",
            requested_orders=len(orders),
            filled_orders=len(fills),
            rejected_orders=len(rejections),
            fills=fills,
            rejections=rejections,
            acceptance_history=acceptance_history,
            rejection_telemetry=rejection_telemetry,
            per_strategy_stats=per_strategy_stats,
            fill_rate=fill_rate,
            average_slippage_bps=avg_slippage_bps,
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