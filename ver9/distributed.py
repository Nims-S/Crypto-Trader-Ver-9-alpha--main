from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any

from .artifacts import ArtifactManager, build_artifact
from .generation import generate_candidates
from .lifecycle import auto_promote
from .portfolio import allocate
from .registry import upsert_candidate
from .validation import validate_candidate


@dataclass(slots=True)
class WorkerBatchResult:
    worker_id: str
    batch_index: int
    processed: int = 0
    promoted: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DistributedEvolutionSummary:
    generated: int
    processed: int
    promoted: int
    failed: int
    worker_count: int
    max_workers: int
    portfolio_size: int
    portfolio: list[dict[str, Any]] = field(default_factory=list)
    batch_results: list[dict[str, Any]] = field(default_factory=list)
    artifact_path: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DistributedEvolutionError(RuntimeError):
    pass


class DistributedEvolutionWorker:
    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id

    def process_batch(
        self,
        batch: list[dict[str, Any]],
        *,
        batch_index: int,
        folds: int,
        mc_iterations: int,
        perturbation_trials: int,
    ) -> WorkerBatchResult:
        result = WorkerBatchResult(worker_id=self.worker_id, batch_index=batch_index)

        for candidate in batch:
            result.processed += 1
            strategy_id = str(candidate.get("strategy_id") or "unknown")

            try:
                validation = validate_candidate(
                    candidate,
                    folds=folds,
                    iterations=mc_iterations,
                    trials=perturbation_trials,
                )
                merged = dict(candidate)
                validation_dict = validation.as_dict()
                merged["validation"] = validation_dict
                merged["validation_passed"] = bool(
                    validation_dict["walk_forward"]["passed"]
                    and validation_dict["monte_carlo"]["passed"]
                    and validation_dict["perturbation"]["passed"]
                    and validation_dict["cross_symbol"]["passed"]
                )
                merged["strategy_evidence"] = validation_dict["evidence"]
                merged["robustness_score"] = max(
                    float(merged.get("robustness_score") or 0.0),
                    float(validation_dict["evidence"]["robustness_score"] or 0.0),
                    float(validation_dict["cross_symbol"]["mean_score"] or 0.0),
                    float(validation_dict["monte_carlo"]["score"] or 0.0),
                    float(validation_dict["perturbation"]["stability_score"] or 0.0),
                )
                merged["walk_forward"] = validation_dict["walk_forward"]
                merged["monte_carlo"] = validation_dict["monte_carlo"]
                merged["perturbation"] = validation_dict["perturbation"]
                merged["cross_symbol"] = validation_dict["cross_symbol"]
                merged = auto_promote(merged)
                upsert_candidate(merged)
                result.candidates.append(merged)
                result.promoted += 1
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.errors.append(f"{strategy_id}: {exc}")

        return result


class DistributedEvolutionCoordinator:
    def __init__(self, *, worker_count: int = 4, batch_size: int = 8) -> None:
        self.worker_count = max(1, int(worker_count))
        self.batch_size = max(1, int(batch_size))

    def _chunk(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        return [items[index : index + self.batch_size] for index in range(0, len(items), self.batch_size)]

    def run(
        self,
        *,
        iterations: int = 5,
        folds: int = 4,
        mc_iterations: int = 500,
        perturbation_trials: int = 100,
        max_positions: int = 3,
        cycle_id: str = "distributed_cycle",
        artifact_dir: str = "artifacts",
    ) -> DistributedEvolutionSummary:
        generated = generate_candidates(iterations=iterations)
        batches = self._chunk(generated)

        batch_results: list[WorkerBatchResult] = []
        promoted_candidates: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.worker_count) as executor:
            future_map = {
                executor.submit(
                    DistributedEvolutionWorker(worker_id=f"worker-{index % self.worker_count}").process_batch,
                    batch,
                    batch_index=index,
                    folds=folds,
                    mc_iterations=mc_iterations,
                    perturbation_trials=perturbation_trials,
                ): index
                for index, batch in enumerate(batches)
            }

            for future in as_completed(future_map):
                batch_index = future_map[future]
                try:
                    batch_result = future.result()
                except Exception as exc:  # noqa: BLE001
                    batch_result = WorkerBatchResult(
                        worker_id=f"worker-{batch_index % self.worker_count}",
                        batch_index=batch_index,
                        failed=len(batches[batch_index]),
                        errors=[f"batch_{batch_index}: {exc}"],
                    )
                batch_results.append(batch_result)
                promoted_candidates.extend(batch_result.candidates)

        deployable = [
            row
            for row in promoted_candidates
            if row.get("status") in {"validated", "probationary", "deployable"}
        ]
        portfolio = allocate(deployable, max_positions=max_positions)

        artifact = build_artifact(
            cycle_id=cycle_id,
            config={
                "iterations": iterations,
                "folds": folds,
                "mc_iterations": mc_iterations,
                "perturbation_trials": perturbation_trials,
                "worker_count": self.worker_count,
                "batch_size": self.batch_size,
                "max_positions": max_positions,
            },
            survivors=deployable,
            portfolio=portfolio,
            protections=[{"status": "distributed_worker_run"}],
        )
        artifact_path = ArtifactManager(base_dir=artifact_dir).save(artifact)

        processed = sum(batch.processed for batch in batch_results)
        promoted = sum(batch.promoted for batch in batch_results)
        failed = sum(batch.failed for batch in batch_results)

        return DistributedEvolutionSummary(
            generated=len(generated),
            processed=processed,
            promoted=promoted,
            failed=failed,
            worker_count=self.worker_count,
            max_workers=self.worker_count,
            portfolio_size=len(portfolio),
            portfolio=portfolio,
            batch_results=[batch.as_dict() for batch in sorted(batch_results, key=lambda item: item.batch_index)],
            artifact_path=str(artifact_path),
        )
