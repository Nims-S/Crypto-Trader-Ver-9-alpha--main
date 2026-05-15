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
from ver9.state import summarize_state
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



def cmd_evolve(args: argparse.Namespace) -> None:
    generated = generate_candidates(iterations=args.iterations)

    promoted: list[dict] = []
    validation_summaries: list[dict] = []

    for row in generated:
        validation = validate_candidate(row, folds=args.folds, iterations=args.mc_iterations, trials=args.perturbation_trials)
        merged = _merge_validation(row, validation.as_dict())

        basket_context = diversity_report(promoted).as_dict() if promoted else {}
        basket_context["selected_count"] = len(promoted)
        basket_context["max_positions"] = args.max_positions

        promoted_row = auto_promote(merged, basket_context=basket_context)
        promoted.append(promoted_row)

        validation_summaries.append({
            "strategy_id": promoted_row.get("strategy_id"),
            "validation_passed": promoted_row.get("validation_passed", False),
            "validation_score": promoted_row.get("validation_score", 0.0),
            "status": promoted_row.get("status"),
        })
        upsert_candidate(promoted_row)

    deployable = [
        row
        for row in promoted
        if row.get("status") in {"validated", "probationary", "deployable"}
    ]

    portfolio = allocate(
        deployable,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
        soft_fill=not args.strict,
    )

    artifact = build_artifact(
        cycle_id=args.cycle_id,
        config={
            "iterations": args.iterations,
            "max_positions": args.max_positions,
            "min_positions": args.min_positions,
            "strict": args.strict,
            "folds": args.folds,
            "mc_iterations": args.mc_iterations,
            "perturbation_trials": args.perturbation_trials,
        },
        survivors=deployable,
        portfolio=portfolio,
        protections=[{"status": "active"}],
    )

    artifact_path = ArtifactManager().save(artifact)

    dump(
        {
            "generated": len(generated),
            "survivors": len(deployable),
            "portfolio_size": len(portfolio),
            "artifact": str(artifact_path),
            "portfolio": portfolio,
            "basket": portfolio_summary(
                deployable,
                max_positions=args.max_positions,
                min_positions=args.min_positions,
                soft_fill=not args.strict,
            ),
            "diversity": diversity_report(deployable).as_dict(),
            "validation_summaries": validation_summaries[:20],
        },
        args.output_file,
    )



def _registry_candidates(args: argparse.Namespace) -> list[dict]:
    return list_candidates(
        status=args.status,
        family=args.family,
        symbol=args.symbol,
    )



def cmd_basket(args: argparse.Namespace) -> None:
    rows = _registry_candidates(args)
    summary = basket_summary(
        rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
        soft_fill=not args.strict,
    )
    dump(summary, args.output_file)



def cmd_portfolio_strict(args: argparse.Namespace) -> None:
    rows = _registry_candidates(args)
    portfolio = strict_portfolio(rows, max_positions=args.max_positions)
    dump({"portfolio": portfolio, "mode": "strict"}, args.output_file)



def cmd_portfolio_probationary(args: argparse.Namespace) -> None:
    rows = _registry_candidates(args)
    portfolio = probationary_portfolio(
        rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
    )
    dump({"portfolio": portfolio, "mode": "probationary"}, args.output_file)



def cmd_diversity(args: argparse.Namespace) -> None:
    rows = _registry_candidates(args)
    dump(diversity_report(rows).as_dict(), args.output_file)



def cmd_generation_quota(args: argparse.Namespace) -> None:
    dump(generation_quota_report(args.iterations), args.output_file)



def cmd_distributed(args: argparse.Namespace) -> None:
    coordinator = DistributedEvolutionCoordinator(
        worker_count=args.worker_count,
        batch_size=args.batch_size,
    )
    summary = coordinator.run(
        iterations=args.iterations,
        folds=args.folds,
        mc_iterations=args.mc_iterations,
        perturbation_trials=args.perturbation_trials,
        max_positions=args.max_positions,
        cycle_id=args.cycle_id,
        artifact_dir=args.artifact_dir,
    )
    dump(summary.as_dict(), args.output_file)



def cmd_registry(args: argparse.Namespace) -> None:
    rows = list_candidates(
        status=args.status,
        family=args.family,
        symbol=args.symbol,
    )
    dump(rows, args.output_file)



def cmd_registry_summary(args: argparse.Namespace) -> None:
    dump(summarize_registry(), args.output_file)



def cmd_execute(args: argparse.Namespace) -> None:
    allocation_rows = list_candidates(status=args.status, family=args.family, symbol=args.symbol)
    allocations = allocate(
        allocation_rows,
        max_positions=args.max_positions,
        min_positions=args.min_positions,
        soft_fill=not args.strict,
    )
    summary = execute_allocations(allocations, capital=args.capital, live=args.live)
    dump(summary.as_dict(), args.output_file)



def cmd_risk(args: argparse.Namespace) -> None:
    monitor = RiskMonitor()
    if args.mode == "portfolio":
        state = monitor.evaluate_portfolio(
            portfolio_drawdown_pct=args.drawdown,
            rolling_loss_streak=args.loss_streak,
            volatility_regime_score=args.volatility,
        )
        dump(state.as_dict(), args.output_file)
        return

    drift = monitor.evaluate_drift(
        strategy_id=args.strategy_id,
        live_metrics={
            "return_pct": args.live_return,
            "max_drawdown_pct": args.live_drawdown,
        },
        expected_metrics={
            "return_pct": args.expected_return,
            "max_drawdown_pct": args.expected_drawdown,
        },
    )
    dump(drift.as_dict(), args.output_file)



def cmd_daemon(args: argparse.Namespace) -> None:
    if args.forever:
        cycles = run_daemon_forever(
            capital=args.capital,
            max_positions=args.max_positions,
            live=args.live,
            cycle_interval_seconds=args.cycle_interval_seconds,
            max_cycles=args.max_cycles,
        )
        dump({"cycles": cycles, "mode": "continuous"}, args.output_file)
        return

    cycle = run_daemon_once(capital=args.capital, max_positions=args.max_positions, live=args.live)
    dump(cycle, args.output_file)



def cmd_state(args: argparse.Namespace) -> None:
    dump(summarize_state(), args.output_file)



def cmd_artifact(args: argparse.Namespace) -> None:
    manager = ArtifactManager()
    artifact = build_artifact(
        cycle_id=args.cycle_id,
        config={"mode": "alpha"},
        survivors=[{"strategy_id": "btc_mr_alpha"}],
        portfolio=[{"symbol": "BTC/USDT", "allocation": 0.4}],
        protections=[{"status": "approved"}],
    )
    path = manager.save(artifact)
    dump({"artifact_path": str(path)}, args.output_file)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="main.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("universe")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_universe)

    p = sub.add_parser("protections")
    p.add_argument("--drawdown", type=float, default=-4.0)
    p.add_argument("--loss-streak", type=int, default=1)
    p.add_argument("--volatility", type=float, default=0.5)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_protections)

    p = sub.add_parser("evolve")
    p.add_argument("--iterations", type=int, default=5)
    p.add_argument("--folds", type=int, default=4)
    p.add_argument("--mc-iterations", type=int, default=500)
    p.add_argument("--perturbation-trials", type=int, default=100)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--min-positions", type=int, default=2)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--cycle-id", default="cycle_alpha")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_evolve)

    p = sub.add_parser("basket")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--min-positions", type=int, default=2)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_basket)

    p = sub.add_parser("portfolio-strict")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_portfolio_strict)

    p = sub.add_parser("portfolio-probationary")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--min-positions", type=int, default=2)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_portfolio_probationary)

    p = sub.add_parser("diversity")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_diversity)

    p = sub.add_parser("generation-quota")
    p.add_argument("--iterations", type=int, default=5)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_generation_quota)

    p = sub.add_parser("distributed-evolve")
    p.add_argument("--iterations", type=int, default=5)
    p.add_argument("--folds", type=int, default=4)
    p.add_argument("--mc-iterations", type=int, default=500)
    p.add_argument("--perturbation-trials", type=int, default=100)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--worker-count", type=int, default=4)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--cycle-id", default="distributed_cycle")
    p.add_argument("--artifact-dir", default="artifacts")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_distributed)

    p = sub.add_parser("registry")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_registry)

    p = sub.add_parser("registry-summary")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_registry_summary)

    p = sub.add_parser("execute")
    p.add_argument("--capital", type=float, default=10000.0)
    p.add_argument("--live", action="store_true")
    p.add_argument("--status", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--symbol", default=None)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--min-positions", type=int, default=2)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_execute)

    p = sub.add_parser("risk")
    p.add_argument("--mode", choices=["portfolio", "drift"], default="portfolio")
    p.add_argument("--drawdown", type=float, default=-4.0)
    p.add_argument("--loss-streak", type=int, default=1)
    p.add_argument("--volatility", type=float, default=0.5)
    p.add_argument("--strategy-id", default="demo_strategy")
    p.add_argument("--live-return", type=float, default=0.0)
    p.add_argument("--expected-return", type=float, default=0.0)
    p.add_argument("--live-drawdown", type=float, default=0.0)
    p.add_argument("--expected-drawdown", type=float, default=0.0)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_risk)

    p = sub.add_parser("daemon")
    p.add_argument("--capital", type=float, default=10000.0)
    p.add_argument("--max-positions", type=int, default=3)
    p.add_argument("--live", action="store_true")
    p.add_argument("--forever", action="store_true")
    p.add_argument("--cycle-interval-seconds", type=float, default=5.0)
    p.add_argument("--max-cycles", type=int, default=None)
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_daemon)

    p = sub.add_parser("state")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("artifact")
    p.add_argument("--cycle-id", default="cycle_alpha")
    p.add_argument("--output-file", default=None)
    p.set_defaults(func=cmd_artifact)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
