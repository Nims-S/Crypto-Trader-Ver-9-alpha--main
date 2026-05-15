from __future__ import annotations

MUTATION_SPACES = {
    "mean_reversion": {
        "zscore_window": [10, 14, 20, 30, 50],
        "reclaim_threshold": [0.8, 1.0, 1.2, 1.5],
        "volatility_band": [1.5, 2.0, 2.5, 3.0],
        "cooldown_bars": [1, 2, 3, 5],
    },
    "trend": {
        "atr_multiplier": [1.5, 2.0, 2.5, 3.0],
        "breakout_window": [20, 30, 50, 100],
        "momentum_threshold": [0.5, 1.0, 1.5],
        "continuation_bars": [2, 3, 5, 8],
    },
    "volatility_compression": {
        "compression_window": [10, 20, 30],
        "squeeze_threshold": [0.15, 0.2, 0.25],
        "expansion_trigger": [1.2, 1.5, 2.0],
        "breakout_confirmation": [1, 2, 3],
    },
}


def get_mutation_space(family: str) -> dict:
    return MUTATION_SPACES.get(family, {})
