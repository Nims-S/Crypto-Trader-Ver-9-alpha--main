from __future__ import annotations

import asyncio
import hmac
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from ver9.runtime.exchanges.websocket_client import (
    ExchangeWebsocketClient,
    WebsocketClientConfig,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BinanceRuntimeConfig:
    api_key: str
    api_secret: str
    websocket_url: str = "wss://fstream.binance.com/ws"
    listen_key: str | None = None


class BinanceRuntimeSession:
    """
    Live Binance runtime integration.

    Responsibilities:
    - authenticated websocket sessions
    - account stream subscriptions
    - order stream ingestion
    - execution event routing
    - runtime event normalization
    - reconnect/re-auth handling
    """

    def __init__(
        self,
        config: BinanceRuntimeConfig,
        event_handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        self.config = config
        self.event_handler = event_handler

        self.client = ExchangeWebsocketClient(
            WebsocketClientConfig(url=config.websocket_url),
            message_handler=self._handle_message,
            auth_handler=self._authenticate,
        )

    async def start(self) -> None:
        await self.client.start()

    async def stop(self) -> None:
        await self.client.stop()

    async def subscribe_market_streams(self, symbols: list[str]) -> None:
        streams = [f"{symbol.lower()}@bookTicker" for symbol in symbols]

        payload = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time()),
        }

        await self.client.subscribe(payload)

    async def subscribe_account_stream(self) -> None:
        if not self.config.listen_key:
            logger.warning("No Binance listen key configured")
            return

        payload = {
            "method": "SUBSCRIBE",
            "params": [self.config.listen_key],
            "id": int(time.time()),
        }

        await self.client.subscribe(payload)

    async def _authenticate(self, socket) -> None:
        timestamp = int(time.time() * 1000)

        signature_payload = f"timestamp={timestamp}"

        signature = hmac.new(
            self.config.api_secret.encode(),
            signature_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        payload = {
            "method": "LOGIN",
            "params": {
                "apiKey": self.config.api_key,
                "timestamp": timestamp,
                "signature": signature,
            },
            "id": timestamp,
        }

        await socket.send(json.dumps(payload))

    async def _handle_message(self, payload: dict) -> None:
        normalized = self._normalize_event(payload)
        await self.event_handler(normalized)

    def _normalize_event(self, payload: dict) -> dict:
        event_type = payload.get("e", "UNKNOWN")

        return {
            "exchange": "BINANCE",
            "event_type": event_type,
            "timestamp": payload.get("E", int(time.time() * 1000)),
            "payload": payload,
            "sequence": payload.get("u") or payload.get("runtime_sequence"),
        }
