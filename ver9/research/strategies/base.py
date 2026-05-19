from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class Signal:
    timestamp: str
    symbol: str
    side: str
    confidence: float
    metadata: dict[str, Any]


class Strategy(ABC):
    strategy_id: str
    family: str

    @abstractmethod
    def generate_signals(
        self,
        frame: pd.DataFrame,
    ) -> list[Signal]:
        raise NotImplementedError
