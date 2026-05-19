from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class SessionHealth(str, Enum):
    CONNECTING = "CONNECTING"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    HALTED = "HALTED"


@dataclass(slots=True)
class SessionMetrics:
    reconnect_count: int = 0
    heartbeat_failures: int = 0
    last_message_ts: float = 0.0
    last_heartbeat_ts: float = 0.0
    sequence_gap_count: int = 0


@dataclass(slots=True)
class ExchangeSessionConfig:
    exchange: str
    stale_after_seconds: int = 20
    heartbeat_interval_seconds: int = 10
    reconnect_backoff_seconds: int = 5
    max_reconnect_attempts: int = 50


class ExchangeSessionManager:
    """
    Runtime exchange session supervisor.

    Responsibilities:
    - websocket lifecycle
    - reconnect supervision
    - stale stream detection
    - heartbeat supervision
    - sequence tracking
    - auth refresh scheduling
    """

    def __init__(
        self,
        config: ExchangeSessionConfig,
        connect_handler: Callable[[], Awaitable[None]],
        disconnect_handler: Callable[[], Awaitable[None]],
        auth_refresh_handler: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        self.config = config
        self._connect_handler = connect_handler
        self._disconnect_handler = disconnect_handler
        self._auth_refresh_handler = auth_refresh_handler

        self.metrics = SessionMetrics()
        self.health = SessionHealth.DISCONNECTED

        self._running = False
        self._last_sequence: Optional[int] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        await self._connect()
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()

        await self._disconnect_handler()
        self.health = SessionHealth.DISCONNECTED

    async def register_message(self, sequence: Optional[int] = None) -> None:
        now = time.time()
        self.metrics.last_message_ts = now
        self.metrics.last_heartbeat_ts = now

        if sequence is not None:
            self._track_sequence(sequence)

    async def heartbeat(self) -> None:
        self.metrics.last_heartbeat_ts = time.time()

    async def refresh_authentication(self) -> None:
        if self._auth_refresh_handler is None:
            return

        logger.info("Refreshing exchange authentication for %s", self.config.exchange)
        await self._auth_refresh_handler()

    async def force_reconnect(self, reason: str) -> None:
        logger.warning(
            "Forcing reconnect for %s due to: %s",
            self.config.exchange,
            reason,
        )

        self.health = SessionHealth.RECONNECTING
        self.metrics.reconnect_count += 1

        await self._disconnect_handler()
        await asyncio.sleep(self.config.reconnect_backoff_seconds)
        await self._connect()

    async def _connect(self) -> None:
        self.health = SessionHealth.CONNECTING
        await self._connect_handler()
        self.health = SessionHealth.ACTIVE

        now = time.time()
        self.metrics.last_message_ts = now
        self.metrics.last_heartbeat_ts = now

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_staleness()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Exchange session monitor failure")
                self.health = SessionHealth.WARNING if hasattr(SessionHealth, 'WARNING') else SessionHealth.RECONNECTING

    async def _check_staleness(self) -> None:
        age = time.time() - self.metrics.last_message_ts

        if age <= self.config.stale_after_seconds:
            return

        logger.warning(
            "Detected stale exchange stream for %s age=%s",
            self.config.exchange,
            round(age, 2),
        )

        self.health = SessionHealth.STALE
        await self.force_reconnect("stale_stream")

    def _track_sequence(self, sequence: int) -> None:
        if self._last_sequence is None:
            self._last_sequence = sequence
            return

        if sequence <= self._last_sequence:
            logger.warning(
                "Out-of-order sequence detected exchange=%s current=%s previous=%s",
                self.config.exchange,
                sequence,
                self._last_sequence,
            )
            self.metrics.sequence_gap_count += 1

        self._last_sequence = sequence
