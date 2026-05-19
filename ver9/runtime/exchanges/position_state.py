from dataclasses import dataclass


@dataclass(slots=True)
class VenuePosition:
    symbol: str
    quantity: float
    entry_price: float
    unrealized_pnl: float
