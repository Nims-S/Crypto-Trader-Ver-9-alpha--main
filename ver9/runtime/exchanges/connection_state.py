from dataclasses import dataclass


@dataclass(slots=True)
class ConnectionState:
    connected: bool
    latency_ms: float
    updated_at: str
