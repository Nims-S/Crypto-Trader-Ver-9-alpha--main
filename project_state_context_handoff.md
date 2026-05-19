# PROJECT_STATE.md

## Current Goal

Build a resilient multi-strategy crypto trading research and execution platform with:

- Autonomous strategy evolution
- Robust strategy validation
- Portfolio-aware allocation
- Runtime state transitions
- Recovery/quarantine lifecycle management
- Execution-quality-aware portfolio construction
- Regression-safe architecture evolution

The current focus is:

1. Stable daemon/runtime execution
2. Reliable registry persistence and recovery
3. Basket construction consistency
4. Execution telemetry realism
5. Regression coverage for critical architecture contracts
6. Better runtime explainability and state visibility

---

# Current Errors

## Latest Known Runtime Issues (Mostly Resolved)

Previously encountered:

- JSONDecodeError during state recovery
- Missing runtime state APIs
- Empty basket selection despite populated registry
- Runtime cycles producing no fills/rejections
- Basket contract drift after allocator modifications
- Recovery/quarantine cleanup inconsistencies
- Atomic save regressions
- Registry recovery failures

## Current Remaining Risks / Watch Areas

### Thin Registry Risk

Daemon can still operate with very small candidate pools.

Current mitigation:
- Fallback ladder:
  - deployable
  - probationary
  - validated
- Thin basket telemetry
- Explicit selection source tracking

### Runtime Consistency Risk

Still monitoring:
- Multi-cycle daemon consistency
- Recovery state cleanup
- Quarantine transitions
- Basket health after distributed evolve

### Batch/Observability Risk

Current batch improvements added:
- Pre/post evolution diversity snapshots
- Post distributed-evolve basket snapshots
- Single consolidated log output

---

# Completed Features

## Research Engine

Implemented:

- Strategy evolution loop
- Distributed evolution
- Strategy mutation
- Validation scoring
- Monte Carlo validation
- Walk-forward validation
- Cross-symbol validation
- Perturbation testing
- Robustness scoring

## Strategy Registry

Implemented:

- Registry persistence
- Atomic registry save
- Registry recovery
- Status lifecycle:
  - validated
  - probationary
  - deployable
  - active
  - quarantined
  - retired

## Basket Construction

Implemented:

- Diversity-aware selection
- Correlation penalty
- Family caps
- Allocation caps
- Cash weighting
- Promotion-aware allocation
- Execution-quality-aware allocation
- Strict basket contracts
- Thin pool rejection logic

## Runtime / Daemon

Implemented:

- daemon-once CLI
- daemon-forever CLI
- Runtime cycle persistence
- Execution telemetry
- Fill simulation
- Rejection simulation
- Execution quality scoring
- Transition summaries
- Selection fallback ladder
- Thin basket reporting
- Candidate source telemetry
- Selection reason telemetry

## Recovery / Safety

Implemented:

- Quarantine flow
- Recovery flow
- Risk approval pipeline
- Rolling risk telemetry
- Recovery cleanup
- Atomic state writes
- Regression coverage

## Regression Coverage

Added tests for:

- Basket contract
- Registry recovery
- Atomic saves
- Quarantine cleanup
- Runtime transitions
- Fallback ladder behavior
- Recovery state machine

---

# Pending Tasks

## High Priority

### Runtime Realism

Improve:
- Multi-position execution realism
- Position aging
- Exit logic integration
- Live PnL tracking
- Portfolio exposure tracking

### Execution Layer

Add:
- Partial fill realism
- Latency simulation
- Order queue simulation
- Liquidity-aware sizing
- Slippage curve modeling

### Portfolio Intelligence

Enhance:
- Regime-aware allocations
- Dynamic capital multipliers
- Portfolio volatility targeting
- Cross-strategy covariance estimation
- Capital efficiency scoring

### Research Engine

Planned:
- Offline evolutionary clusters
- Autonomous parameter search
- Strategy lineage tracking
- Research memory
- Meta-strategy scoring

### Infrastructure

Planned:
- Scheduler integration
- Long-running daemon supervisor
- Production monitoring
- Metrics dashboard
- Auto-recovery watchdog

---

# Deployment Links

## Deployment Platform

Current deployment targets referenced in project:

### Render

Used for:
- FastAPI runtime hosting
- Background daemon hosting
- API deployment

Typical launch command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Neon PostgreSQL

Database provider:
- Neon serverless PostgreSQL

Connection style:

```text
postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
```

---

# Important Commands

## Research / Evolution

```bash
python main.py evolve
```

```bash
python main.py distributed-evolve
```

## Basket / Portfolio

```bash
python main.py basket
```

```bash
python main.py portfolio-strict
```

```bash
python main.py portfolio-probationary
```

## Runtime

```bash
python main.py daemon-once
```

```bash
python main.py daemon-forever --max-cycles 3
```

## Diagnostics

```bash
python main.py complete-state
```

```bash
python main.py registry-summary
```

```bash
python main.py diversity
```

## Batch Testing

```bash
run_all_tests.bat
```

---

# Architecture Notes

## System Architecture

The project is intentionally separated into layers.

## 1. Research Engine

Purpose:
- Generate and evolve strategies
- Run validation pipelines
- Score robustness
- Produce registry-ready candidates

Components:
- Evolution loop
- Monte Carlo engine
- Walk-forward validation
- Cross-symbol testing
- Perturbation engine

Future integrations discussed:
- OpenClaw
- Hermes
- Claude Code

## 2. Strategy Registry

Purpose:
- Store validated strategies
- Maintain lifecycle state
- Persist telemetry
- Recover safely after failure

Lifecycle states:

```text
validated
probationary
deployable
active
quarantined
retired
```

## 3. Portfolio / Basket Engine

Purpose:
- Construct diversified baskets
- Apply family caps
- Apply covariance penalties
- Allocate capital intelligently

Current allocator behavior:
- Promotion-aware
- Execution-quality-aware
- Correlation-adjusted
- Thin-basket-aware

## 4. Runtime Execution Layer

Purpose:
- Execute runtime cycles
- Simulate fills/rejections
- Maintain execution telemetry
- Generate lifecycle transitions

Current runtime telemetry includes:

- fill_rate
- execution_quality_score
- average_slippage_bps
- rejection telemetry
- transition summaries
- candidate source counts
- selection reason

## 5. Recovery / Safety Layer

Purpose:
- Quarantine unstable strategies
- Recover healthy strategies
- Preserve runtime integrity
- Prevent corrupted persistence

Includes:
- Atomic state writes
- Recovery cleanup
- Registry recovery
- Safety guardrails

---

# Current Core Files

## bot.py

Responsibilities:
- Runtime orchestration
- Exchange interaction
- Signal execution
- Position handling
- Runtime cycle management
- Risk gating

Referenced features:
- websocket/live feed integration
- execution telemetry
- daemon loop
- runtime state transitions

## strategy.py

Responsibilities:
- Signal generation
- Indicator computation
- Strategy logic
- Parameter handling
- Trade setup generation

Referenced functionality:
- generate_signal()
- compute_indicators()
- StrategyState dataclass
- Signal dataclass

---

# Exchange Used

Current exchange integration:

## CCXT

Used via:

```python
import ccxt
```

Primary trading pairs seen in runtime:

- BTC/USDT
- ETH/USDT
- SOL/USDT

Current runtime mode:
- paper trading

---

# Database Setup

## PostgreSQL (Neon)

Used for:
- strategy persistence
- runtime telemetry
- portfolio state
- execution records

Connection characteristics:
- SSL required
- cloud-hosted
- serverless PostgreSQL

Referenced modules:

```python
from db import get_conn
```

---

# Latest Runtime Snapshot

Most recent stable runtime behavior:

- daemon-once succeeded
- runtime generated fills
- execution telemetry populated
- state transitions recorded
- transition summary emitted
- fallback ladder functioning correctly
- thin basket telemetry functioning correctly

Example transition:

```text
from: deployable
to: active
reason: execution_full_fill
```

---

# Latest Traceback / Error Context

Most recent major historical errors:

```text
JSONDecodeError during runtime state recovery
```

```text
invalid choice: 'daemon-once'
```

```text
No module named main
```

These were addressed by:

- explicit daemon CLI aliases
- corrected runtime invocation
- atomic state save
- registry recovery fixes
- regression coverage

---

# Current Runtime Health

Current status:

- Runtime operational
- Registry persistence stable
- Daemon producing transitions
- Execution telemetry populated
- Regression suite passing
- Batch logging improved

Primary remaining optimization focus:

- Runtime realism
- Portfolio intelligence
- Recovery sophistication
- Research engine autonomy
- Multi-cycle consistency hardening

---

# Recommended New Chat Prompt

Use this project state as context.

This is a multi-strategy crypto trading research and execution platform with:

- research engine
- strategy registry
- portfolio allocator
- runtime daemon
- lifecycle state machine
- recovery/quarantine system
- execution telemetry
- regression-tested architecture

Continue from the current architecture state without removing existing guardrails or fallback ladder behavior.

