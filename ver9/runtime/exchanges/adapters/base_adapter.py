from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(slots=True)
class AdapterState:
    exchange_name: str
    connected: bool
    authenticated: bool
    last_heartbeat: str
    reconnect_attempts: int


class BaseExchangeAdapter:
    """
    Base runtime exchange adapter.

    Responsibilities:
    - websocket lifecycle supervision
    - heartbeat tracking
    - reconnect orchestration
    - authenticated stream state
    - rate-limit awareness
    """

    def __init__(
        self,
        *,
        exchange_name: str,
    ) -> None:
        self.exchange_name = exchange_name

        self.state = AdapterState(
            exchange_name=exchange_name,
            connected=False,
            authenticated=False,
            last_heartbeat=datetime.now(UTC).isoformat(),
            reconnect_attempts=0,
        )

    def connect(self) -> None:
        self.state.connected = True
        self._heartbeat()

    def disconnect(self) -> None:
        self.state.connected = False
        self._heartbeat()

    def authenticate(self) -> None:
        self.state.authenticated = True
        self._heartbeat()

    def reconnect(self) -> None:
        self.state.reconnect_attempts += 1
        self.state.connected = True
        self._heartbeat()

    def _heartbeat(self) -> None:
        self.state.last_heartbeat = (
            datetime.now(UTC).isoformat()
        )
