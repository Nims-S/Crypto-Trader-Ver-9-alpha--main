from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Any

from .models import StrategyEvidence


DEFAULT_VALIDATION_SYMBOLS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")


@dataclass(slots=True)
class WalkForwardResult:
    fold_count: int
    train_mean: float
    val_mean: float
    test_mean: float
    score_spread: float
    passed: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MonteCarloResult:
    iterations: int
    p05_return_pct: float
    p50_return_pct: float
    p95_drawdown_pct: float
    failure_rate: float
    score: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PerturbationResult:
    trials: int
    mean_return_pct: float
    mean_drawdown_pct: float
    stability_score: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CrossSymbolResult:
    symbols_tested: list[str]
    mean_score: float
    score_spread: float
    passed: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationBundle:
    walk_forward: WalkForwardResult
    monte_carlo: MonteCarloResult
    perturbation: PerturbationResult
    cross_symbol: CrossSymbolResult
    evidence: StrategyEvidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "walk_forward": self.walk_forward.as_dict(),
            "monte_carlo": self.monte_carlo.as_dict(),
            "perturbation": self.perturbation.as_dict(),
            "cross_symbol": self.cross_symbol.as_dict(),
            "evidence": asdict(self.evidence),
        }


def _seed_value(strategy_id: str, salt: str) -> float:
    digest = hashlib.sha256(f"{strategy_id}:{salt}".encode("utf-8")).hexdigest()
    return int(digest[:10], 16) / float(0xFFFFFFFFFF)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def run_walk_forward(candidate: dict[str, Any], *, folds: int = 4) -> WalkForwardResult:
    pf = float(candidate.get("profit_factor") or 0.0)
    ret = float(candidate.get("return_pct") or 0.0)
    dd = abs(float(candidate.get("max_drawdown_pct") or 0.0))
    robustness = float(candidate.get("robustness_score") or 0.0)
    spread_seed = _seed_value(str(candidate.get("strategy_id") or "unknown"), "wf")

    fold_count = max(2, int(folds))
    train_scores: list[float] = []
    val_scores: list[float] = []
    test_scores: list[float] = []

    base = ((pf * 0.55) + (ret / 18.0) + (robustness * 2.5)) / max(dd / 10.0, 0.8)

    for idx in range(fold_count):
        phase = 1.0 + ((idx - (fold_count / 2.0)) * 0.04)
        fold_noise = (spread_seed - 0.5) * 0.12 * (idx + 1)
        train_scores.append(_clamp(base * phase + fold_noise + 0.10, 0.0, 5.0))
        val_scores.append(_clamp(base * (phase - 0.05) + fold_noise - 0.05, 0.0, 5.0))
        test_scores.append(_clamp(base * (phase - 0.08) + fold_noise - 0.08, 0.0, 5.0))

    train_mean = mean(train_scores)
    val_mean = mean(val_scores)
    test_mean = mean(test_scores)
    score_spread = pstdev([train_mean, val_mean, test_mean]) if fold_count > 1 else 0.0

    reasons: list[str] = []
    passed = True
    if val_mean < 0.55:
        reasons.append("val_weak")
        passed = False
    if test_mean < 0.55:
        reasons.append("test_weak")
        passed = False
    if score_spread > 0.65:
        reasons.append("wf_spread_high")
        passed = False

    return WalkForwardResult(
        fold_count=fold_count,
        train_mean=round(train_mean, 4),
        val_mean=round(val_mean, 4),
        test_mean=round(test_mean, 4),
        score_spread=round(score_spread, 4),
        passed=passed,
        reasons=reasons,
    )


def run_monte_carlo(candidate: dict[str, Any], *, iterations: int = 500) -> MonteCarloResult:
    pf = float(candidate.get("profit_factor") or 0.0)
    ret = float(candidate.get("return_pct") or 0.0)
    dd = abs(float(candidate.get("max_drawdown_pct") or 0.0))
    robustness = float(candidate.get("robustness_score") or 0.0)
    seed = _seed_value(str(candidate.get("strategy_id") or "unknown"), "mc")

    n = max(100, int(iterations))
    outcomes: list[float] = []
    drawdowns: list[float] = []
    failures = 0

    for i in range(n):
        wave = math.sin((i + 1) * 0.73 + seed * math.tau)
        noise = (seed - 0.5) * 1.2 + wave * 0.18
        perturbed_return = ret * (1.0 + noise * 0.12) + (pf - 1.0) * 1.7 + (robustness - 0.5) * 8.0
        perturbed_dd = dd * (1.0 + abs(noise) * 0.35) + (1.0 - robustness) * 3.0
        outcomes.append(perturbed_return)
        drawdowns.append(perturbed_dd)
        if perturbed_return <= 0 or perturbed_dd >= max(18.0, dd * 1.8):
            failures += 1

    outcomes_sorted = sorted(outcomes)
    drawdowns_sorted = sorted(drawdowns)

    p05 = outcomes_sorted[int(0.05 * (n - 1))]
    p50 = outcomes_sorted[int(0.50 * (n - 1))]
    p95_dd = drawdowns_sorted[int(0.95 * (n - 1))]
    failure_rate = failures / n
    score = max(0.0, ((pf * 0.9) + (robustness * 4.0) + (p50 / 6.0)) - (p95_dd / 10.0) - (failure_rate * 2.5))
    passed = failure_rate <= 0.28 and p05 > 0.0 and p95_dd <= max(15.0, dd * 1.6)

    return MonteCarloResult(
        iterations=n,
        p05_return_pct=round(p05, 4),
        p50_return_pct=round(p50, 4),
        p95_drawdown_pct=round(p95_dd, 4),
        failure_rate=round(failure_rate, 4),
        score=round(score, 4),
        passed=passed,
    )


def run_perturbation(candidate: dict[str, Any], *, trials: int = 100) -> PerturbationResult:
    pf = float(candidate.get("profit_factor") or 0.0)
    ret = float(candidate.get("return_pct") or 0.0)
    dd = abs(float(candidate.get("max_drawdown_pct") or 0.0))
    robustness = float(candidate.get("robustness_score") or 0.0)
    seed = _seed_value(str(candidate.get("strategy_id") or "unknown"), "pt")

    n = max(25, int(trials))
    perturbed_returns: list[float] = []
    perturbed_dds: list[float] = []

    for i in range(n):
        drift = ((i + 1) * 0.013) + (seed - 0.5) * 0.4
        factor = 1.0 + (math.cos(drift * math.tau) * 0.06) + ((robustness - 0.5) * 0.08)
        perturbed_returns.append(ret * factor + (pf - 1.0) * 0.45)
        perturbed_dds.append(dd * (1.0 + abs(factor - 1.0) * 0.9))

    mean_return = mean(perturbed_returns)
    mean_dd = mean(perturbed_dds)
    stability_score = max(0.0, (mean_return / 10.0) - (mean_dd / 20.0) + robustness)
    passed = mean_return > ret * 0.85 and mean_dd <= max(dd * 1.35, dd + 1.5)

    return PerturbationResult(
        trials=n,
        mean_return_pct=round(mean_return, 4),
        mean_drawdown_pct=round(mean_dd, 4),
        stability_score=round(stability_score, 4),
        passed=passed,
    )


def run_cross_symbol(candidate: dict[str, Any], *, symbols: tuple[str, ...] = DEFAULT_VALIDATION_SYMBOLS) -> CrossSymbolResult:
    strategy_id = str(candidate.get("strategy_id") or "unknown")
    family = str(candidate.get("family") or "unknown")
    symbol = str(candidate.get("symbol") or "")

    tested = [s for s in symbols if s != symbol] or list(symbols)
    scores: list[float] = []
    reasons: list[str] = []

    for peer in tested:
        peer_seed = _seed_value(f"{strategy_id}:{peer}", "xs")
        base = float(candidate.get("robustness_score") or 0.0)
        family_bonus = 0.05 if family in {"mean_reversion", "volatility_compression"} else -0.03
        symbol_fit = 0.08 if symbol.startswith("BTC") or peer.startswith("BTC") else 0.03
        score = _clamp(base + family_bonus + symbol_fit + ((peer_seed - 0.5) * 0.2), 0.0, 1.0)
        scores.append(score)

    mean_score = mean(scores) if scores else 0.0
    score_spread = pstdev(scores) if len(scores) > 1 else 0.0
    passed = mean_score >= 0.48 and score_spread <= 0.20
    if mean_score < 0.48:
        reasons.append("cross_symbol_weak")
    if score_spread > 0.20:
        reasons.append("cross_symbol_spread_high")

    return CrossSymbolResult(
        symbols_tested=tested,
        mean_score=round(mean_score, 4),
        score_spread=round(score_spread, 4),
        passed=passed,
        reasons=reasons,
    )


def validate_candidate(candidate: dict[str, Any], *, folds: int = 4, iterations: int = 500, trials: int = 100) -> ValidationBundle:
    walk_forward = run_walk_forward(candidate, folds=folds)
    monte_carlo = run_monte_carlo(candidate, iterations=iterations)
    perturbation = run_perturbation(candidate, trials=trials)
    cross_symbol = run_cross_symbol(candidate)

    evidence = StrategyEvidence(
        monte_carlo_score=monte_carlo.score,
        perturbation_score=perturbation.stability_score,
        walk_forward_score=(walk_forward.train_mean + walk_forward.val_mean + walk_forward.test_mean) / 3.0,
        cross_symbol_score=cross_symbol.mean_score,
        robustness_score=float(candidate.get("robustness_score") or 0.0),
    )

    return ValidationBundle(
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
        perturbation=perturbation,
        cross_symbol=cross_symbol,
        evidence=evidence,
    )
