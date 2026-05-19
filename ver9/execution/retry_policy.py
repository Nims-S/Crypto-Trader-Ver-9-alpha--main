from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryPolicyConfig:
    max_attempts: int = 5
    base_delay_seconds: float = 1.0


class ExecutionRetryPolicy:
    """
    Execution retry supervision.

    Responsibilities:
    - retry orchestration
    - backoff scheduling
    - retry exhaustion handling
    """

    def __init__(self, config: RetryPolicyConfig | None = None) -> None:
        self.config = config or RetryPolicyConfig()

    async def execute(self, operation, *args, **kwargs):
        last_error = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as exc:
                last_error = exc

                delay = self.config.base_delay_seconds * attempt

                logger.warning(
                    "Execution retry attempt=%s delay=%s error=%s",
                    attempt,
                    delay,
                    exc,
                )

                await asyncio.sleep(delay)

        raise RuntimeError(
            f"execution retries exhausted: {last_error}"
        )
