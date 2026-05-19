from dataclasses import dataclass


@dataclass(slots=True)
class MarketView:
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    volume: float
    source_name: str
