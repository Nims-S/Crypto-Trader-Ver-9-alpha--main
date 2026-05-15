from __future__ import annotations

import tempfile
from pathlib import Path

import ver9.distributed as distributed
import ver9.registry as registry


class TempRegistry:
    def __enter__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_registry = registry.REGISTRY_PATH
        self.original_dist_registry = distributed.upsert_candidate
        registry.REGISTRY_PATH = Path(self.tmpdir.name) / "registry.json"
        return registry.REGISTRY_PATH

    def __exit__(self, exc_type, exc, tb):
        registry.REGISTRY_PATH = self.original_registry
        self.tmpdir.cleanup()


class TestDistributedWorker:
    def test_worker_isolates_batch_failures(self) -> None:
        with TempRegistry():
            worker = distributed.DistributedEvolutionWorker(worker_id="worker-1")
            batch = [
                {
                    "strategy_id": "good_1",
                    "profit_factor": 2.4,
                    "return_pct": 7.0,
                    "max_drawdown_pct": -4.0,
                    "robustness_score": 0.84,
                    "trades": 60,
                    "status": "candidate",
                },
                {
                    "strategy_id": "bad_1",
                    "profit_factor": 1.2,
                    "return_pct": 1.0,
                    "max_drawdown_pct": -10.0,
                    "robustness_score": 0.5,
                    "trades": 12,
                    "status": "candidate",
                },
            ]

            original_validate = distributed.validate_candidate
            original_auto_promote = distributed.auto_promote
            original_upsert = distributed.upsert_candidate

            def fake_validate(candidate, *, folds, iterations, trials):
                if candidate["strategy_id"] == "bad_1":
                    raise RuntimeError("validation failed")
                return original_validate(candidate, folds=folds, iterations=iterations, trials=trials)

            def fake_auto_promote(record):
                record = dict(record)
                record["status"] = "validated"
                return record

            captured: list[dict] = []

            def fake_upsert(record):
                captured.append(record)
                return record

            distributed.validate_candidate = fake_validate
            distributed.auto_promote = fake_auto_promote
            distributed.upsert_candidate = fake_upsert
            try:
                result = worker.process_batch(
                    batch,
                    batch_index=0,
                    folds=4,
                    mc_iterations=150,
                    perturbation_trials=40,
                )
            finally:
                distributed.validate_candidate = original_validate
                distributed.auto_promote = original_auto_promote
                distributed.upsert_candidate = original_upsert

            assert result.processed == 2
            assert result.promoted == 1
            assert result.failed == 1
            assert any("validation failed" in error for error in result.errors)
            assert len(result.candidates) == 1
            assert captured and captured[0]["strategy_id"] == "good_1"

    def test_coordinator_runs_and_builds_portfolio(self) -> None:
        with TempRegistry():
            coordinator = distributed.DistributedEvolutionCoordinator(worker_count=2, batch_size=4)

            original_generate = distributed.generate_candidates
            original_validate = distributed.validate_candidate
            original_upsert = distributed.upsert_candidate
            original_auto_promote = distributed.auto_promote

            generated = [
                {
                    "strategy_id": f"cand_{i}",
                    "family": "mean_reversion" if i % 2 == 0 else "volatility_compression",
                    "symbol": "BTC/USDT" if i % 3 == 0 else "ETH/USDT" if i % 3 == 1 else "SOL/USDT",
                    "timeframe": "1h",
                    "regime": "adaptive",
                    "profit_factor": 2.2 + (i * 0.01),
                    "return_pct": 5.0 + i,
                    "max_drawdown_pct": -4.0,
                    "robustness_score": 0.8,
                    "trades": 45,
                    "status": "candidate",
                }
                for i in range(6)
            ]

            def fake_generate_candidates(iterations):
                return list(generated)

            def fake_validate(candidate, *, folds, iterations, trials):
                return original_validate(candidate, folds=folds, iterations=iterations, trials=trials)

            def fake_auto_promote(record):
                record = dict(record)
                record["status"] = "validated"
                return record

            def fake_upsert(record):
                return record

            distributed.generate_candidates = fake_generate_candidates
            distributed.validate_candidate = fake_validate
            distributed.auto_promote = fake_auto_promote
            distributed.upsert_candidate = fake_upsert
            try:
                summary = coordinator.run(
                    iterations=3,
                    folds=4,
                    mc_iterations=150,
                    perturbation_trials=40,
                    max_positions=2,
                    cycle_id="test_distributed_cycle",
                    artifact_dir=str(Path(tempfile.gettempdir()) / "v9_test_artifacts"),
                )
            finally:
                distributed.generate_candidates = original_generate
                distributed.validate_candidate = original_validate
                distributed.upsert_candidate = original_upsert
                distributed.auto_promote = original_auto_promote

            assert summary.generated == len(generated)
            assert summary.processed == len(generated)
            assert summary.failed == 0
            assert summary.promoted == len(generated)
            assert summary.portfolio_size == 2
            assert summary.artifact_path
            assert len(summary.batch_results) >= 1
            assert all("strategy_id" in allocation for allocation in summary.portfolio)
