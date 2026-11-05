# Development Plan

Development is delivered in small, reviewable chunks. A module is not considered
complete merely because its code exists.

## Delivery protocol for every chunk

1. Research the domain, provider documentation, exchange rules, and relevant
   implementation constraints.
2. Write down assumptions, open questions, and the proposed interface.
3. Implement the smallest coherent increment.
4. Add unit tests, edge-case tests, and fixtures; avoid live network calls in unit
   tests.
5. Run tests, linting, and type checks selected for that module.
6. Review correctness, security, data provenance, and failure behavior.
7. Commit the chunk to `development`, summarize changed files and test results,
   and wait for review before moving to the next chunk.

Do not bundle unrelated modules into one commit. Do not push unfinished work to
`main`.

## Proposed sequence

### Phase 1 — Project foundation
- Python package layout and build metadata.
- Test and lint configuration.
- Architecture and development documentation.
- Basic CI validation.

### Phase 2 — Indian market reference data
- Instrument identity and symbol mapping.
- Exchange/session calendar abstraction.
- Normalized quote and OHLCV domain models.
- Data-quality validation and provider contracts.

### Phase 3 — Market-data provider adapters
- Select and document initial provider(s).
- Authentication and secret handling.
- Rate limits, retries, caching, and data freshness.
- Historical and live-data capability boundaries.

### Phase 4 — Research modules
- Market regime.
- Scanner.
- Technical analysis.
- Fundamental analysis.
- News and corporate intelligence.

### Phase 5 — Trade decision modules
- Entry and exit planning.
- Risk manager.
- Portfolio manager.
- Trade journal and review.

### Phase 6 — Validation and user workflows
- Backtesting and walk-forward evaluation.
- Paper-trading workflow.
- Reports and alerts.
- AI skill packages and tool adapters.

### Phase 7 — Optional integrations
- Broker integration, only after a separate safety and regulatory review.
- Hosting, dashboard, scheduling, and notification deployment.

## Completion criteria

A module must have documented inputs/outputs, explicit error behavior, tests for
normal and boundary cases, no embedded secrets, and a clear statement of known
limitations before it is marked complete.
