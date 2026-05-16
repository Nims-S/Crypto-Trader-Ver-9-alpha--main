from __future__ import annotations

import argparse
import json
from pathlib import Path

from ver9.artifacts import ArtifactManager, build_artifact
from ver9.basket_optimizer import basket_summary
from ver9.daemon import run_daemon_forever, run_daemon_once
from ver9.distributed import DistributedEvolutionCoordinator
from ver9.diversity import diversity_report
from ver9.execution import execute_allocations
from ver9.generation import (
    generate_candidates,
    generation_quota_report,
)
from ver9.lifecycle import auto_promote
from ver9.portfolio import allocate, portfolio_summary, probationary_portfolio, strict_portfolio
from ver9.protections import ProtectionEngine
from ver9.registry import list_candidates, summarize_registry, upsert_candidate
from ver9.risk import RiskMonitor
from ver9.state import append_execution, summarize_state
from ver9.universe import DEFAULT_UNIVERSE, PairUniverseManager
from ver9.validation import validate_candidate


def dump(payload: dict | list, output_file: str | None = None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    if output_file:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def cmd_universe(args: argparse.Namespace) -> None:
    manager = PairUniverseManager()
    approved = manager.evaluate(DEFAULT_UNIVERSE)
    dump({"approved_universe": approved}, args.output_file)



def cmd_protections(args: argparse.Namespace) -> None:
    engine = ProtectionEngine()
    decision = engine.evaluate(
        portfolio_drawdown_pct=args.drawdown,
        rolling_loss_streak=args.loss_streak,
        volatility_regime_score=args.volatility,
    )
    dump(decision.__dict__, args.output_file)



def _merge_validation(row: dict, validation: dict) -> dict:
    merged = dict(row)
    merged["validation"] = validation

    wf = validation.get("walk_forward") or {}
    mc = validation.get("monte_carlo") or {}
    pt = validation.get("perturbation") or {}
    xs = validation.get("cross_symbol") or {}
    evidence = validation.get("evidence") or {}

    merged["walk_forward"] = wf
    merged["monte_carlo"] = mc
    merged["perturbation"] = pt
    merged["cross_symbol"] = xs
    merged["strategy_evidence"] = evidence

    merged["walk_forward_score"] = evidence.get("walk_forward_score", 0.0)
    merged["monte_carlo_score"] = evidence.get("monte_carlo_score", 0.0)
    merged["perturbation_score"] = evidence.get("perturbation_score", 0.0)
    merged["cross_symbol_score"] = evidence.get("cross_symbol_score", 0.0)

    merged["robustness_score"] = max(
        float(merged.get("robustness_score") or 0.0),
        float(evidence.get("robustness_score") or 0.0),
        float(evidence.get("cross_symbol_score") or 0.0),
        float(mc.get("score") or 0.0),
        float(pt.get("stability_score") or 0.0),
    )

    merged["profit_factor"] = float(merged.get("profit_factor") or 0.0)
    merged["return_pct"] = float(merged.get("return_pct") or 0.0)
    merged["max_drawdown_pct"] = float(merged.get("max_drawdown_pct") or 0.0)
    merged["trades"] = int(merged.get("trades") or 0)
    merged["validation_passed"] = bool(
        wf.get("passed") and mc.get("passed") and pt.get("passed") and xs.get("passed")
    )
    merged["validation_score"] = round(
        (
            float(wf.get("train_mean") or 0.0)
            + float(wf.get("val_mean") or 0.0)
            + float(wf.get("test_mean") or 0.0)
            + float(mc.get("score") or 0.0)
            + float(pt.get("stability_score") or 0.0)
            + float(xs.get("mean_score") or 0.0)
        )
        / 6.0,
        4,
    )

    return merged


def _with_allocation_telemetry(summary: dict) -> dict:
    payload = dict(summary)
    payload["allocation_telemetry"] = summary.get("allocation_telemetry", {})
    return payload


def cmd_basket(args: argparse.Namespace) -> None:
    rows = list_candidates(
        status=args.status,
        family=args.family,
        symbol=args.symbol,
    )
    summary = basket_summary(
        rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
        soft_fill=not args.strict,
    )
    dump(_with_allocation_telemetry(summary), args.output_file)


def cmd_portfolio_probationary(args: argparse.Namespace) -> None:
    rows = list_candidates(
        status=args.status,
        family=args.family,
        symbol=args.symbol,
    )

    portfolio = probationary_portfolio(
        rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
    )

    basket = basket_summary(
        rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
        soft_fill=True,
    )

    dump(
        {
            "mode": "probationary",
            "portfolio": portfolio,
            "basket": basket,
            "allocation_telemetry": basket.get("allocation_telemetry", {}),
        },
        args.output_file,
    )
