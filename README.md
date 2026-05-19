# Crypto-Trader-Ver-9-alpha

Ver9 is transitioning from a synthetic strategy research shell into a real quantitative research and portfolio experimentation platform.

The project now contains:
- real market data ingestion
- real strategy execution
- real backtesting
- portfolio-level simulation
- walk-forward validation
- experiment tracking
- regime classification
- typed runtime infrastructure

It is NOT yet a production trading system.

The current focus is:
building reliable research infrastructure before autonomous optimization.

---

# Current System State

## What Is Real

### Research Infrastructure

Implemented:

- Typed runtime models
- Typed lifecycle transitions
- Portfolio allocation engine
- Strategy registry persistence
- Quarantine/recovery lifecycle system
- Execution telemetry
- Experiment tracking
- Experiment ranking
- Regime-aware strategy routing

---

### Real Market Data Pipeline

Implemented:

```text
Binance OHLCV download
→ normalization
→ validation
→ parquet persistence
→ research engine
```

Current components:

```text
ver9/research/data/connectors/binance.py
ver9/research/data/validation.py
ver9/research/data/market_data.py
```

Capabilities:

- Binance historical downloads
- Incremental dataset merging
- Timestamp normalization
- Deduplication
- Data integrity validation
- Parquet storage

---

### Real Strategy Framework

Implemented:

```text
ver9/research/strategies/
```

Current strategies:

#### SMA Cross Baseline

Purpose:
- benchmark strategy
- regression sanity check
- trend-following baseline

#### Lorentzian Classification Strategy

Current implementation includes:

- RSI features
- CCI features
- ROC features
- Lorentzian distance metric
- nearest-neighbor classification
- EMA trend filtering
- anti-leakage future labeling

Important:
This is a research hypothesis engine.
Not validated alpha.

---

### Backtesting Infrastructure

Implemented:

```text
ver9/research/backtesting/
```

Capabilities:

- Strategy-level backtesting
- Portfolio-level backtesting
- Shared capital simulation
- Exposure constraints
- Confidence-weighted sizing
- Fee modeling
- Slippage modeling
- Walk-forward validation

Portfolio engine currently supports:

- multiple concurrent strategies
- capital contention
- exposure caps
- portfolio equity curves
- portfolio-level Sharpe/drawdown metrics

---

### Experiment Tracking

Implemented:

```text
ver9/research/experiments/
```

Capabilities:

- experiment persistence
- parameter lineage
- metric lineage
- walk-forward summaries
- ranking/scoring
- reproducible experiment snapshots
- atomic save semantics

This is the foundation for future:
- hyperparameter optimization
- distributed research
- meta-learning
- adaptive strategy governance

---

### Market Regime Infrastructure

Implemented:

```text
ver9/research/regime/
```

Capabilities:

- volatility regime classification
- trend regime classification
- liquidity regime classification
- adaptive strategy routing
- strategy enable/disable gating
- regime-aware allocation scaling

Current regime model is heuristic-based.
Not institutional-grade state inference.

---

# What Was Removed Conceptually

The project originally relied heavily on synthetic strategy generation.

Earlier versions generated fake metrics from deterministic hash functions.

That architecture is being phased out.

The following areas are still legacy/synthetic:

```text
generation.py
validation.py
mutation_spaces.py
quota_tuner.py
```

These systems are NOT currently trusted as real alpha research.

The migration strategy is:
replace synthetic evaluation with real data-driven research incrementally.

---

# Current Architectural Direction

The current roadmap prioritizes:

```text
research correctness
→ reproducibility
→ risk realism
→ adaptive governance
→ live execution
```

NOT:

```text
blind strategy generation
```

---

# Major Current Limitations

Ver9 is still NOT production-grade.

Missing or incomplete:

- realistic order book simulation
- spread dynamics
- partial fills
- funding rates
- leverage/liquidation simulation
- market impact modeling
- correlation shock modeling
- latency simulation
- deterministic experiment seeds
- feature store/versioning
- benchmark governance
- survivorship-bias controls
- true out-of-sample orchestration
- exchange reconciliation
- production execution daemon hardening

Current execution assumptions are still optimistic.

---

# Current Research Philosophy

The objective is NOT to create an "AI trading bot" quickly.

The objective is:

```text
build a disciplined adaptive research platform
that can safely evolve toward autonomous portfolio management
without uncontrolled overfitting.
```

That requires:

- reproducibility
- regime awareness
- risk governance
- realistic validation
- strict leakage prevention
- capital-aware portfolio simulation

before:

- reinforcement learning
- genetic optimization
- autonomous mutation systems
- self-improving agents

---

# Current Repo Structure

```text
ver9/
├── research/
│   ├── backtesting/
│   ├── data/
│   ├── experiments/
│   ├── regime/
│   ├── strategies/
│   ├── validation/
│   └── examples/
│
├── daemon/
├── execution/
├── lifecycle/
├── portfolio/
└── registry/
```

---

# Immediate Next Priorities

Highest-priority upcoming work:

1. Feature infrastructure
2. Leakage-resistant feature pipelines
3. Feature lineage/versioning
4. Better execution realism
5. Portfolio covariance/risk modeling
6. Robust out-of-sample governance
7. Live paper-trading integration
8. Exchange reconciliation layer
9. Adaptive portfolio weighting
10. Safer evolutionary research replacement

---

# Status Summary

Ver9 is now:

```text
a legitimate early-stage quantitative research platform
```

It is no longer:

```text
pure infrastructure theater around synthetic metrics
```

But it is also NOT yet:

```text
a deployable institutional trading system
```

The project is currently in the transition phase between those two states.
