from dataclasses import dataclass


@dataclass(slots=True)
class ConnectionHealth:
    connection_state: str
    latency_ms: float
    reconnect_attempts: int


class ConnectionHealthTracker:
    def __init__(self) -> None:
        self.reconnect_attempts = 0

    def evaluate(
        self,
        *,
        latency_ms: float,
        connected: bool,
    ) -> ConnectionHealth:
        state = "connected"

        if not connected:
            state = "disconnected"
            self.reconnect_attempts += 1

        elif latency_ms > 1500:
            state = "degraded"

        return ConnectionHealth(
            connection_state=state,
            latency_ms=round(latency_ms, 4),
            reconnect_attempts=self.reconnect_attempts,
        )
