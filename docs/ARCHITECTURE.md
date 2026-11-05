# Architecture

## Product objective

Build a platform-independent research and decision-support system for Indian equity
swing trading. The initial product identifies, researches, ranks, and monitors
potential trades. Live order execution is explicitly out of scope for the initial
release.

## Architectural principles

1. **Core first, interfaces second.** Trading calculations and domain rules live in
   the Python package, not inside a particular AI assistant or hosting platform.
2. **Skills orchestrate; code calculates.** Agent skills describe repeatable
   workflows. Deterministic, tested Python code performs calculations and validates
   data.
3. **Provider independence.** Market-data and broker integrations sit behind
   interfaces. Strategy code must not depend directly on Groww, NSE, or another
   vendor.
4. **Evidence before conclusions.** Market facts carry source, instrument, interval,
   timestamp, and freshness metadata wherever applicable.
5. **No fabricated data.** Missing, stale, delayed, or unavailable data must be
   represented explicitly and must not silently become a valid signal.
6. **Risk before recommendation.** A candidate is not a qualified trade until it
   passes configured liquidity, risk, and reward-to-risk checks.
7. **Research before execution.** Initial releases produce research and paper-trade
   outputs. Live order placement requires a separate future design and explicit
   approval.
8. **Testability and reproducibility.** Domain calculations should be deterministic
   and testable without network access or a running server.

## Logical layers

### 1. User and agent interfaces

- Claude-compatible Agent Skills.
- ChatGPT/Codex-compatible Agent Skills and tool integrations where supported.
- Command-line interface for local execution.
- Future dashboard and notification adapters.

These are adapters, not the owners of trading logic.

### 2. Skill and workflow layer

Skills coordinate tasks such as market-regime review, stock screening, technical
analysis, fundamental research, news review, trade qualification, and post-trade
review. Skills call approved tools or application services; they do not invent
prices or independently substitute for deterministic calculations.

### 3. Application and domain layer

Owns instrument identity, normalized market data, indicators, screening rules,
research results, strategy evaluation, risk checks, portfolio state, backtesting,
and reporting.

### 4. Infrastructure adapters

Provide replaceable implementations for market data, company disclosures, news,
storage, notifications, and (later) brokers.

## Initial package boundaries

The first implementation modules are expected to evolve toward:

- `market_data`: provider contracts, normalized bars/quotes, data-quality checks.
- `instruments`: NSE/BSE instrument identity and symbol mapping.
- `indicators`: deterministic technical calculations.
- `fundamentals`: normalized company financial metrics and quality checks.
- `news`: sourced news and corporate-event records.
- `strategies`: screening and entry/exit rules.
- `risk`: position sizing and trade/portfolio constraints.
- `portfolio`: holdings, watchlists, and trade records.
- `backtesting`: historical simulation with costs and bias controls.
- `interfaces`: CLI, agent tools, and future API adapters.

Do not create all these modules as empty folders in the foundation phase. Add each
when its contract and tests are designed.

## Data and safety requirements

- Store timestamps with explicit timezone semantics; exchange session logic uses
  Asia/Kolkata.
- Distinguish exchange timestamps from retrieval timestamps.
- Preserve provider and source attribution.
- Validate missing candles, duplicate records, impossible OHLC relationships, and
  suspicious volume/price values.
- Adjust historical analysis for corporate actions where the data source supports it.
- Backtests must account for brokerage, taxes/fees, slippage, liquidity, and
  realistic order fills.
- Avoid look-ahead bias and survivorship bias.
- Never present a model-generated probability as statistically calibrated unless
  validated against out-of-sample data.
- Keep credentials out of source control and logs.

## Decisions intentionally deferred

- Hosting and deployment target.
- Final broker and broker API.
- Paid versus broker-provided market-data plan.
- Final stock universe and liquidity thresholds.
- Exact holding-period rules and strategy parameters.
- Capital allocation and risk limits.
- Dashboard, alert channel, and scheduling technology.

These choices should be made when the relevant module is designed, not guessed in
the project foundation.
