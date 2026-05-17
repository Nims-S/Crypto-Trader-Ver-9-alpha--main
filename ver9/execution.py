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
    execution_quality_score: float = 0.0
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



def _build_telemetry(orders: list[OrderRequest], fills: list[dict[str, Any]], rejections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], float, float, float]:
    request_by_strategy: dict[str, int] = Counter()
    fill_by_strategy: dict[str, int] = Counter()
    reject_by_strategy: dict[str, int] = Counter()
    slippage_by_strategy: dict[str, list[float]] = defaultdict(list)
    rejection_reasons: Counter[str] = Counter()
    acceptance_history: list[dict[str, Any]] = []

    fills_by_key = {(str(f.get("strategy_id") or ""), str(f.get("symbol") or ""), str(f.get("side") or ""), round(float(f.get("quantity") or 0.0), 8)): f for f in fills}

    for order in orders:
        request_by_strategy[order.strategy_id] += 1
        fill = fills_by_key.get((order.strategy_id, order.symbol, order.side, round(float(order.quantity), 8)))
        accepted = fill is not None
        fill_price = float(fill.get("fill_price") or 0.0) if fill else None
        slippage = round(_slippage_bps(order.price, fill_price), 4) if fill else None
        rejection_reason = None
        if accepted:
            fill_by_strategy[order.strategy_id] += 1
            slippage_by_strategy[order.strategy_id].append(slippage or 0.0)
        else:
            reject_by_strategy[order.strategy_id] += 1
            rejection_reason = next((r.get("reason") for r in rejections if str(r.get("strategy_id") or "") == order.strategy_id), "unfilled")
            rejection_reasons[str(rejection_reason or "unfilled")] += 1

        acceptance_history.append({
            "strategy_id": order.strategy_id,
            "symbol": order.symbol,
            "side": order.side,
            "requested_quantity": round(float(order.quantity), 8),
            "expected_price": round(float(order.price or 0.0), 4) if order.price is not None else None,
            "fill_price": round(float(fill_price or 0.0), 4) if fill_price is not None else None,
            "accepted": accepted,
            "fill_ratio": round(_stable_ratio(f"{order.strategy_id}:{order.symbol}:{order.side}:{order.quantity}"), 4),
            "slippage_bps": slippage,
            "rejection_reason": rejection_reason,
        })

    per_strategy_stats: dict[str, Any] = {}
    for strategy_id in sorted(set(request_by_strategy) | set(fill_by_strategy) | set(reject_by_strategy)):
        req = request_by_strategy.get(strategy_id, 0)
        fills_n = fill_by_strategy.get(strategy_id, 0)
        rej = reject_by_strategy.get(strategy_id, 0)
        slippage_values = slippage_by_strategy.get(strategy_id, [])
        fill_rate = (fills_n / req) if req else 0.0
        avg_slip = (sum(slippage_values) / len(slippage_values)) if slippage_values else 0.0
        per_strategy_stats[strategy_id] = {
            "requested_orders": req,
            "filled_orders": fills_n,
            "rejected_orders": rej,
            "fill_rate": round(fill_rate, 6),
            "average_slippage_bps": round(avg_slip, 4),
            "execution_quality_score": round(max(0.0, (fill_rate * 0.55) + ((1.0 - min(abs(avg_slip) / 250.0, 1.0)) * 0.45)), 6),
        }

    fill_rate = round((len(fills) / len(orders)) if orders else 0.0, 6)
    all_slippage = [x for vals in slippage_by_strategy.values() for x in vals]
    avg_slippage = round((sum(all_slippage) / len(all_slippage)) if all_slippage else 0.0, 4)
    rejection_telemetry = {"reasons": dict(rejection_reasons), "total_rejections": len(rejections), "unique_strategies_rejected": len(reject_by_strategy)}
    execution_quality_score = round(max(0.0, min(1.0, (fill_rate * 0.5) + ((1.0 - min(abs(avg_slippage) / 250.0, 1.0)) * 0.35) + ((1.0 - (len(rejections) / len(orders) if orders else 0.0)) * 0.15))), 6)
    return acceptance_history, rejection_telemetry, per_strategy_stats, fill_rate, avg_slippage, execution_quality_score


class PaperBroker:
    def __init__(self, *, equity: float = 10000.0, fill_threshold: float = 0.35) -> None:
        self.equity = equity
        self.fill_threshold = fill_threshold

    def submit(self, orders: list[OrderRequest]) -> ExecutionSummary:
        fills: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        committed = 0.0
        for order in orders:
            ratio = _stable_ratio(f"{order.strategy_id}:{order.symbol}:{order.side}:{order.quantity}")
            if ratio < self.fill_threshold:
                order.status = "rejected"
                rejections.append({"strategy_id": order.strategy_id, "symbol": order.symbol, "reason": "fill_simulation_below_threshold", "fill_ratio": round(ratio, 4)})
                continue
            fill_price = order.price if order.price is not None else 100.0 + (ratio * 7.5)
            fills.append({"strategy_id": order.strategy_id, "symbol": order.symbol, "side": order.side, "quantity": round(order.quantity, 8), "fill_price": round(fill_price, 4)})
            committed += float(order.quantity) * float(fill_price)
            order.status = "filled"

        acceptance_history, rejection_telemetry, per_strategy_stats, fill_rate, avg_slippage_bps, exec_quality = _build_telemetry(orders, fills, rejections)
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
            execution_quality_score=exec_quality,
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
        symbol = str(allocation.get("symbol") or "")
        strategy_id = str(allocation.get("strategy_id") or "")
        family = str(allocation.get("family") or "")
        qty = max(0.0, (capital * pct) / 100.0)
        orders.append(OrderRequest(strategy_id=strategy_id, symbol=symbol, side="buy" if family in {"mean_reversion", "volatility_compression"} else "buy", quantity=round(qty, 8), price=100.0 + (_stable_ratio(strategy_id + symbol) * 9.0)))
    return orders



def execute_allocations(allocations: list[dict[str, Any]], *, capital: float, live: bool = False) -> ExecutionSummary:
    broker: Broker = LiveBroker(equity=capital) if live else PaperBroker(equity=capital)
    return broker.submit(build_orders_from_allocations(allocations, capital=capital))
