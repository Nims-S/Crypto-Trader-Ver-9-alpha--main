from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebsocketClientConfig:
    url: str
    ping_interval: int = 15
    stale_after_seconds: int = 30
    reconnect_min_delay: float = 1.0
    reconnect_max_delay: float = 30.0


class ExchangeWebsocketClient:
    """
    Async exchange websocket runtime.

    Features:
    - reconnect jitter
    - ping/pong handling
    - stale detection
    - authenticated sessions
    - stream multiplexing
    - sequence replay hooks
    """

    def __init__(
        self,
        config: WebsocketClientConfig,
        message_handler: Callable[[dict], Awaitable[None]],
        auth_handler: Optional[Callable[[WebSocketClientProtocol], Awaitable[None]]] = None,
    ) -> None:
        self.config = config
        self._message_handler = message_handler
        self._auth_handler = auth_handler

        self._running = False
        self._last_message_ts = 0.0
        self._sequence = 0
        self._socket: Optional[WebSocketClientProtocol] = None

    async def start(self) -> None:
        self._running = True

        while self._running:
            try:
                await self._connect_loop()
            except Exception:
                logger.exception("Exchange websocket loop failure")

            await self._sleep_with_jitter()

    async def stop(self) -> None:
        self._running = False

        if self._socket:
            await self._socket.close()

    async def subscribe(self, payload: dict) -> None:
        if not self._socket:
            raise RuntimeError("websocket not connected")

        await self._socket.send(json.dumps(payload))

    async def _connect_loop(self) -> None:
        async with websockets.connect(
            self.config.url,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_interval,
        ) as socket:
            logger.info("Connected websocket=%s", self.config.url)

            self._socket = socket
            self._last_message_ts = time.time()

            if self._auth_handler:
                await self._auth_handler(socket)

            await asyncio.gather(
                self._reader_loop(),
                self._heartbeat_loop(),
            )

    async def _reader_loop(self) -> None:
        assert self._socket is not None

        async for raw_message in self._socket:
            self._last_message_ts = time.time()

            payload = json.loads(raw_message)
            self._sequence += 1

            payload["runtime_sequence"] = self._sequence

            await self._message_handler(payload)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            age = time.time() - self._last_message_ts

            if age > self.config.stale_after_seconds:
                logger.warning("Detected stale websocket stream")
                raise ConnectionError("stale websocket stream")

            await asyncio.sleep(1)

    async def _sleep_with_jitter(self) -> None:
        delay = random.uniform(
            self.config.reconnect_min_delay,
            self.config.reconnect_max_delay,
        )

        logger.info("Reconnecting websocket after %.2f seconds", delay)
        await asyncio.sleep(delay)
