from dataclasses import dataclass, field


@dataclass(slots=True)
class AssetBalance:
    asset: str
    free_amount: float
    locked_amount: float


@dataclass(slots=True)
class TradingAccountState:
    balances: list[AssetBalance] = field(default_factory=list)
