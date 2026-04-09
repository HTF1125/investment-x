# ix/ Architecture Guide

> **For AI agents and developers:** This is the definitive guide for where code belongs in the `ix/` package.
> When adding new functionality, consult this file before creating or modifying files.

---

## Quick Reference

| Folder | Purpose | Put here if... |
|--------|---------|----------------|
| `core/indicators/` | Macro indicator functions (600+) | You're computing a time series from raw data (FRED, DB) that represents an economic/market signal |
| `core/backtesting/` | Portfolio simulation & strategy framework | You're building a trading strategy, position sizer, or backtest engine component |
| `core/macro/` | Three-horizon macro outlook pipeline | You're working on regime detection, walk-forward IC ranking, or the macro allocation pipeline |
| `common/quantitative/` | Quant analytics (correlation, regression, PCA, VaR, optimization) | You're doing regression, correlation, VaR, portfolio optimization, or factor analysis |
| `core/technical/` | Short-term technical indicators & chart analysis | You're building OHLCV-based timing signals (RSI, Bollinger, Elliott Wave, Supertrend) |
| `common/performance/` | Portfolio performance & attribution | You're computing Sharpe, drawdown, Brinson attribution, or risk metrics |
| `core/regimes/` | Probabilistic regime classification | You're classifying macro states (growth/inflation/liquidity regimes) |
| `core/timeseries_processing.py` | Timeseries data pipeline logic | You're writing search, upload parsing, timezone normalization, or format conversion for timeseries |
| `db/models/` | SQLAlchemy ORM models | You're defining a new database table |
| `db/custom/` | Backward-compat re-export shim | **Do NOT add files here** — it only re-exports from `core/indicators/` |
| `db/` (root) | Connection, session, query helpers | You're adding database infrastructure (caching, connection pooling, query utilities) |
| `api/routers/` | FastAPI HTTP endpoints (thin orchestration) | You're exposing functionality via REST API |
| `api/` (root) | App config, middleware, schemas | You're adding auth, rate limiting, Pydantic schemas, or middleware |
| `collectors/` | External data collection agents | You're pulling data from an external source (API, scraper) into the DB |
| `common/` | Shared utilities & infrastructure | You're writing something used by 2+ modules (logging, dates, formatting) |
| `common/data/` | Data transforms, statistics, scalers, crawlers | You're writing `clean_series`, `Resample`, `RollingZScore`, `StandardScaler`, data fetchers |
| `common/security/` | Auth & sandboxing | You're writing JWT auth, expression validation, or security blocklists |
| `common/viz/` | Chart rendering, theming | You're writing chart/figure helpers, Plotly manipulation, or report generation |
| `common/notify/` | Notifications | You're writing email or Telegram sending logic |

---

## Detailed Module Guide

### `core/` — Computation Engine

Pure Python/Pandas computation. **No HTTP, no database writes, no UI.**
Everything here should be importable and testable without running the server.

#### `core/indicators/` — Macro Indicator Library

**Purpose:** Functions that return `pd.Series` or `pd.DataFrame` representing economic/market indicators.

**Pattern:** Each file is a domain module (e.g., `rates.py`, `credit_deep.py`, `sentiment.py`). All modules are wildcard-imported by `__init__.py`, so every public function is auto-available in the chart expression DSL.

**Namespace classes** group related indicators (e.g., `YieldCurve.us_2s10s()`, `CreditSpreads.hy_spread()`). Use these for DSL discoverability.

**Put here:**
- New indicator functions that compute a signal from raw data
- New namespace classes grouping related indicators
- Example: `def us_credit_impulse() -> pd.Series`

**Do NOT put here:**
- Trading strategies (those go in `core/backtesting/strategies/`)
- API endpoints
- Chart rendering logic

**Naming:** One file per domain — `{domain}.py` (e.g., `liquidity.py`, `volatility.py`). Add to existing file if the domain already exists.

**File index:**
- `growth.py` — GDP, PMI, ISM, manufacturing momentum, OECD CLI diffusion
- `fci.py` — Financial conditions indices
- `liquidity.py` — Central bank balance sheets, money market stress
- `central_bank.py` — Policy rates, asset purchases
- `rates.py` — Yield curves, real rates, breakevens
- `credit_deep.py` — HY/IG spreads, CDX, distress proxies
- `earnings.py` — EPS momentum, revision breadth, deep earnings analysis
- `equity.py` — Valuation (P/E, ERP, Buffett indicator)
- `sentiment.py` — Put/call, AAII, NAAIM positioning, margin debt, fund flows
- `volatility.py` — VIX, VVIX, skew, term structure
- `cross_asset.py` — Dollar index, copper/gold, commodities, sector rotation
- `inflation.py` — CPI surprise, breakeven momentum
- `economy.py` — Nowcasting, recession probability, LEI, consumer health, labor market
- `regional.py` — Korea-specific (OECD CLI, exports), China/EM indicators
- `real_assets.py` — Housing, oil, gold, transportation, energy infrastructure
- `policy.py` — Policy/trade/geopolitical uncertainty, fiscal policy
- `macro.py` — Multi-indicator composites
- `scorecards.py` — Multi-layer scorecards

---

#### `core/backtesting/` — Portfolio Simulation Framework

**Purpose:** Strategy base classes, portfolio tracking, trade execution simulation, and pre-built allocation strategies.

**Subfolders:**
- `engine/` — Core abstractions: `Portfolio`, `Position`, `Strategy` base class, `RiskManager`, analytics
- `strategies/` — Concrete strategy implementations (GTAA, BAA, CDM, defense-first, etc.)
- `batch/` — Batch runner, strategy registry, weight functions for systematic comparison

**Put here:**
- New portfolio strategies (inherit from `Strategy` base class)
- Position sizing logic, rebalancing rules
- Backtest analytics and visualization helpers
- Transaction cost analysis

**Do NOT put here:**
- Indicator computation (→ `core/indicators/`)
- Regime detection (→ `core/regimes/`)
- Database persistence of results (→ `db/models/`)

**Naming:** Strategies go in `strategies/{strategy_name}.py`. Engine components go in `engine/`.

---

#### `core/macro/` — Macro Outlook Pipeline

**Purpose:** The scheduled pipeline that computes the three-horizon macro allocation framework. Runs indicator computation → z-score normalization → regime classification → allocation weights.

**Key components:**
- `pipeline.py` — Orchestrates full computation
- `engine.py` — Signal computation, z-scores, binary regime allocation
- `regime.py` — HPFilter, GMM regime detection
- `taxonomy.py` — 200+ indicator registry mapped to regimes
- `wf_backtest.py` — Walk-forward IC-ranked backtest
- `rolling_ic.py` — Information coefficient computation
- `vol_scaling.py` — Volatility-based position sizing
- `vams.py` — Volatility-adjusted momentum system

**Put here:**
- Enhancements to the macro pipeline computation
- New regime detection algorithms
- Walk-forward backtest improvements
- Indicator taxonomy changes

**Do NOT put here:**
- Individual indicator functions (→ `core/indicators/`)
- API endpoints for macro data (→ `api/routers/analytics/`)

---

#### `core/quantitative/` — Backward-Compat Shim

Re-exports from `common/quantitative/`. **Do not add code here.** Use `from ix.common.quantitative import ...` for new code.

---

#### `core/technical/` — Technical Analysis

**Purpose:** Short-term OHLCV-based timing signals and chart analysis tools.

**Constraint:** Single-ticker, price/volume data only. No macro data, no cross-ticker signals.

**Modules:**
- `bollinger.py`, `rsi.py`, `momentum.py`, `moving_average.py` — Classic indicators
- `trend.py` — Breakouts, MA crossovers
- `regime.py` — Technical regime classification
- `elliott_wave.py` — TDSequential, Elliott Wave detection, swing analysis, Fibonacci scoring
- `ohlcv_indicators.py` — RSI, Squeeze Momentum, Supertrend, Bollinger, VWAP, Stochastic, ATR, support/resistance
- `force_index_composite.py`, `trend_momentum_composite.py` — Multi-layer composites
- `vams_technicals.py` — Volatility-adjusted momentum
- `weekly_regime.py` — Weekly-based regimes

**Put here:**
- New technical indicators computed from OHLCV
- Composite technical systems combining multiple signals
- Chart analysis algorithms (wave counting, pattern detection)

**Do NOT put here:**
- Macro/fundamental indicators (→ `core/indicators/`)
- Anything requiring cross-ticker data
- Plotly figure rendering (→ keep in routers or `common/charting.py`)

---

#### `core/performance/` — Backward-Compat Shim

Re-exports from `common/performance/`. **Do not add code here.** Use `from ix.common.performance import ...` for new code.

---

#### `core/regimes/` — Regime Classification

**Purpose:** Probabilistic state machines for macro regimes.

- `base.py` — Base `Regime` class, z-score utilities
- `macro.py` — `MacroRegime` (4-state: Goldilocks, Reflation, Deflation, Stagflation)
- `liquidity.py` — `LiquidityRegime` (2-state: Easing, Tightening)

**Put here:** New regime classifiers. Inherit from `Regime` base class.

---

#### `core/transforms.py` — Backward-Compat Shim

Re-exports from `common/transforms.py`. **Do not add code here.** Use `from ix.common.transforms import ...` for new code.

---

#### `core/timeseries_processing.py` — Timeseries Data Pipeline

**Purpose:** Search, upload, and format logic for timeseries data. Extracted from the API router to keep routes thin.

**Key functions:**
- `build_search_filter_and_order()` — PostgreSQL FTS + LIKE search/ranking
- `process_bulk_create()` — Excel upload parsing and DB merge
- `process_template_upload()` — Template upload pipeline
- `format_dataframe_to_column_dict()` — DataFrame → JSON-serializable output
- `normalize_timezone()` — Timezone stripping utility

---

#### `core/stress_test.py` — Stress Testing

**Purpose:** Historical stress test analysis for market crash scenarios.

- `compute_stress_test()` — Main entry point

---

### `db/` — Database Layer

#### `db/models/` — ORM Models

**Purpose:** SQLAlchemy model definitions. One model per file (or closely related group).

**Existing models:** `charts`, `chart_pack`, `macro_outlook`, `strategy_result`, `user`, `whiteboard`, `collector_state`, `institutional_holding`, `logs`, `briefing`, `research_source`, `api_cache`, `credit_event`, `report`

**Put here:** New database table definitions. Follow existing pattern: class inherits from `Base`, uses `__tablename__`.

---

#### `db/custom/` — Backward-Compatibility Shim

**Purpose:** `__init__.py` re-exports everything from `ix.core.indicators`. **Do NOT add new files here.** All indicator functions live in `core/indicators/`.

---

#### `db/` (root files)

- `conn.py` — Engine, Session factory, connection pooling
- `query.py` — `Series()` helper for timeseries lookup with caching
- `client.py` — High-level client (`get_timeseries`, utilities)
- `init_db.py` — Schema initialization
- `bm.py` — Benchmark helpers

---

### `api/` — HTTP Layer

**Rule:** Routers should be **thin orchestration**. Heavy computation goes in `core/`, chart rendering in `common/charting.py`. Routers handle auth, validation, error mapping, and response formatting.

#### `api/routers/` — Endpoint Groups

| Router | Prefix | Purpose |
|--------|--------|---------|
| `analytics/` | `/macro`, `/quant`, `/technical`, `/strategies`, `/screener` | Computation endpoints |
| `auth/` | `/auth`, `/admin`, `/user` | Authentication & user management |
| `charts/` | `/charts` | Chart packs, dashboards, expressions, whiteboards |
| `data/` | `/series`, `/timeseries`, `/sources`, `/evaluation`, `/collectors` | Data CRUD |
| `research/` | `/library`, `/news`, `/scorecards`, `/tts` | Research content |
| `risk/` | `/risk` | Risk analytics |

**Put here:** New API endpoints. Create a new router file if the domain doesn't fit existing routers.

**Conventions:**
- Auth: `Depends(get_current_user)` for any user, `Depends(get_current_admin_user)` for admin
- Rate limiting: `_limiter = Limiter(...)` local to router, `request: Request` as FIRST param
- Blocking DB calls: use `def`, not `async def`
- Register new routers in `api/routers/__init__.py`
- **No business logic in routes** — call `core/` for computation, catch `ValueError` and map to `HTTPException`

#### `api/` (root files)

- `main.py` — App initialization, middleware, APScheduler
- `dependencies.py` — Auth, session injection
- `schemas.py` — Pydantic request/response models
- `rate_limit.py` — Rate limiting config
- `spa_serving.py` — Frontend static file serving
- `exceptions.py` — Custom exception handlers

---

### `collectors/` — Data Collection Agents

**Purpose:** ETL agents that pull data from external APIs/websites into the database.

**Pattern:** Each collector inherits from `BaseCollector` and implements `collect(progress_cb)` → `{inserted, updated, errors, message}`. State tracked in `CollectorState` table. Run via APScheduler.

**Existing collectors:** CFTC, CBOE, AAII, NAAIM, Google Trends, SEC 13F, FINRA dark pool, full-text indexer

**Put here:** New data source integrations. One file per source.

**Template:**
```python
from .base import BaseCollector

class MySourceCollector(BaseCollector):
    name = "my_source"
    schedule = "0 6 * * 1-5"  # cron expression

    def collect(self, progress_cb=None):
        # fetch → transform → upsert into DB
        return {"inserted": n, "updated": m, "errors": 0, "message": "ok"}
```

Register in `registry.py`.

---

### `common/` — Shared Utilities & Helper Functions

**Purpose:** Cross-cutting infrastructure, helper functions, and reusable building blocks used by 2+ modules. This is where helper functions live — `core/` is for domain classes and systems.

#### `data/` — Data helpers
- `transforms.py` — `clean_series`, `Resample`, `PctChange`, `Diff`, `MovingAverage`, `StandardScalar`, `Offset`, `Clip`, `Ffill`, `Rebase`, `Drawdown`, `daily_ffill`, `MonthEndOffset`, `CycleForecast`, `SimilarPatterns`
- `statistics.py` — `RollingZScore`, `Cycle`, `VAR`, `STDEV`, `ENTP`, `CV`, `Winsorize`, `empirical_cov`
- `preprocessing.py` — `BaseScaler`, `StandardScaler`, `RobustScaler`, `MinMaxScaler`
- `crawler.py` — Yahoo Finance, FRED, Naver data fetching

#### `security/` — Auth & sandboxing
- `auth.py` — JWT token generation/verification
- `safe_expression.py` — Sandboxed chart expression evaluator
- `safe_custom_code.py` — Sandboxed user code execution
- `blocklists.py` — Blocked attributes/functions for DSL security

#### `viz/` — Visualization
- `charting.py` — Chart rendering, Plotly figure processing, PDF/HTML export, sandboxed code execution
- `theme.py` — Matplotlib/Plotly styling, NBER recession shading

#### `notify/` — Notifications
- `email.py` — Email sending
- `telegram.py` — Telegram notifications

#### `performance/` — Performance analytics
- `metrics.py` — Sharpe, Sortino, Calmar, information ratio, drawdown, capture ratios
- `attribution.py` — Brinson-Fachler attribution, multi-period decomposition, factor return decomposition
- `utils.py` — Quantile helpers, demeaning, performance by state

#### `quantitative/` — Quantitative analytics
- `correlation.py` — Rolling correlation, hierarchical clustering
- `regression.py` — OLS, rolling beta, multi-factor models
- `pca.py` — Principal component analysis
- `var.py` — Value at Risk, expected shortfall
- `estimators.py` — Covariance estimators (Ledoit-Wolf, OAS, exponential), Black-Litterman
- `optimizer.py` — Portfolio optimization, inverse-variance, tracking error
- `factor_lens.py` — Multi-factor attribution (FactorLens)
- `dsl.py` — Chart expression DSL wrappers
- `pattern_search.py` — Time series pattern matching

#### Infrastructure (flat files)
- `logger.py` — `get_logger(name)` structured logging
- `terminal.py` — Terminal UI helpers
- `settings.py` — Config management from env vars
- `date.py` — Date utilities (`today`, `tomorrow`, `onemonthbefore`, period helpers)
- `fmt.py` — Formatting (`as_format`, `as_date`)
- `util.py` — Generic utilities (`all_subclasses`, `ContributionToGrowth`)

#### `task/` — Background task queue utilities

**Put here:**
- Helper functions used across modules (transforms, scalers, formatters)
- Infrastructure (logging, config, auth, notifications)
- Security sandboxing
- Chart rendering / report generation helpers

**Do NOT put here:**
- Domain-specific analytical systems (→ `core/`)
- One-off helpers for a single module (keep them local)

---

## Decision Tree: "Where does my code go?"

```
Is it a new database table?
  → db/models/

Is it an HTTP endpoint?
  → api/routers/{domain}/
  (keep it thin — computation in core/, charting in common/viz/charting.py)

Is it pulling data from an external source into the DB?
  → collectors/

Is it chart rendering, PDF generation, or figure processing?
  → common/viz/charting.py

Is it a reusable data transform (clean, resample, z-score, offset)?
  → common/data/transforms.py

Is it a scaler class (StandardScaler, RobustScaler, MinMaxScaler)?
  → common/data/preprocessing.py

Is it a simple statistical function (VAR, STDEV, Cycle, Winsorize)?
  → common/data/statistics.py

Is it auth, expression sandboxing, or security blocklists?
  → common/security/

Is it a utility used by multiple modules (logging, formatting, dates)?
  → common/

Is it pure computation (domain-specific)?
  ├─ Economic/market indicator (returns pd.Series)?
  │   → core/indicators/{domain}.py
  │
  ├─ OHLCV-based technical signal (single ticker)?
  │   → core/technical/
  │
  ├─ Regime classification (probabilistic state)?
  │   → core/regimes/
  │
  ├─ Portfolio strategy / backtest logic?
  │   → core/backtesting/
  │
  ├─ Macro pipeline / walk-forward / IC ranking?
  │   → core/macro/
  │
  ├─ Performance metrics / attribution?
  │   → common/performance/
  │
  └─ General stats / optimization / risk math?
      → common/quantitative/
```

---

## Naming Conventions

| Module | File naming | Example |
|--------|------------|---------|
| `core/indicators/` | `{domain}.py` | `liquidity.py`, `volatility.py` |
| `core/backtesting/strategies/` | `{strategy_name}.py` | `gtaa.py`, `defense_first.py` |
| `core/technical/` | `{indicator_type}.py` | `bollinger.py`, `elliott_wave.py` |
| `core/regimes/` | `{regime_type}.py` | `macro.py`, `liquidity.py` |
| `db/models/` | `{entity}.py` | `chart_pack.py`, `credit_event.py` |
| `api/routers/` | `{resource}.py` inside domain folder | `analytics/macro.py`, `data/series.py` |
| `collectors/` | `{source}.py` | `cftc.py`, `sec_13f.py` |
| `common/` | `{utility}.py` | `date.py`, `charting.py` |

---

## Key Architectural Rules

1. **Routers are thin.** No computation, no DataFrame manipulation, no chart building. Call `core/` or `common/` and map errors to HTTP responses.
2. **`core/` is for domain systems.** Main analytical classes — indicators, backtesting, regimes, macro pipeline. No simple helper functions.
3. **`common/` is for helpers.** Transforms, scalers, statistics, formatters, infrastructure. Things that are building blocks, not domain systems.
4. **`db/custom/` is frozen.** It's a backward-compat shim. All indicators live in `core/indicators/`.
5. **One canonical `clean_series`.** Use `from ix.common.data.transforms import clean_series`. Don't write your own.
6. **Namespace classes for DSL.** When adding indicators, group them in a namespace class in `core/indicators/__init__.py` for chart expression access.
7. **Backward-compat shims.** `core/transforms.py`, `core/performance/`, `core/quantitative/` are re-export shims. Don't add code to them — use `common/` directly.
