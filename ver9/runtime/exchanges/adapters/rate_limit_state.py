from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(slots=True)
class RateLimitState:
    request_count: int
    window_started_at: str


class RateLimiter:
    def __init__(
        self,
        *,
        max_requests_per_window: int = 1200,
    ) -> None:
        self.max_requests_per_window = (
            max_requests_per_window
        )

        self.state = RateLimitState(
            request_count=0,
            window_started_at=datetime.now(UTC).isoformat(),
        )

    def allow_request(self) -> bool:
        if (
            self.state.request_count
            >= self.max_requests_per_window
        ):
            return False

        self.state.request_count += 1

        return True
