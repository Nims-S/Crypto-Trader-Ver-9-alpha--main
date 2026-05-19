from __future__ import annotations

from typing import Any

from ..ticker_normalizer import TickerNormalizer
from .base_adapter import BaseExchangeAdapter


class BitunixAdapter(BaseExchangeAdapter):
    def __init__(self) -> None:
        super().__init__(exchange_name="bitunix")

        self.normalizer = TickerNormalizer()

    def normalize_ticker(
        self,
        payload: dict[str, Any],
    ):
        return self.normalizer.normalize(
            venue="bitunix",
            payload=payload,
        )
