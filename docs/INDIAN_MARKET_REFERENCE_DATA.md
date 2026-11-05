# Indian Market Reference Data

## Scope of this module

The reference-data foundation supports both NSE and BSE from the beginning.
Initial research and screening may prioritise NSE, but exchange identity is part
of every instrument record so that the same issuer listed on two exchanges is
not accidentally treated as one exchange listing.

## Instrument identity

The canonical exchange-scoped identity is:

`(exchange, symbol, series)`

ISIN is retained as a cross-market issuer/security identifier when supplied, but
is not used as the sole primary key. An ISIN can be shared by listings on more
than one exchange. BSE scrip codes and NSE tokens are retained as provider or
exchange identifiers, not substituted for the canonical identity.

The model preserves the original exchange series because series convey trading
and settlement distinctions. The first research universe will explicitly select
eligible equity series rather than assuming every listed instrument is an
ordinary, liquid cash equity. ETFs, REITs, InvITs, debt, preference shares and
warrants are separately classified.

## Official reference sources

- NSE securities master and market reports expose symbol, ISIN, security code,
  series and corporate-action information:
  https://www.nseindia.com/static/products-services/equity-market-data-reports-download
- NSE securities available for trading, symbol changes and other reference
  lists:
  https://www.nseindia.com/static/market-data/securities-available-for-trading
- NSE series legend explains distinctions such as EQ and trade-for-trade series:
  https://www.nseindia.com/static/market-data/legend-of-series
- NSE exchange holidays and market timings:
  https://www.nseindia.com/resources/exchange-communication-holidays
- BSE equity segment master circular documents its scrip master and trading
  session conventions:
  https://www.bseindia.com/markets/MarketInfo/DownloadAttach.aspx?attachedId=8a7fec3a-95bc-4bd2-82de-76e2a84e2915&id=20250429-51

Exchange reference files and calendars are external data, not constants to
silently freeze in application code. The ingestion layer must record the source,
retrieval timestamp, effective date, and file version where available.

## Session handling

The common continuous equity session is 09:15–15:30 India time for NSE and BSE.
This is not a claim that all sessions are identical: pre-open, special pre-open,
periodic call auction, T+0, block-deal and special trading sessions differ.
The initial calendar model represents the regular continuous session and allows
exchange-specific special sessions to be injected.

Timezone is `Asia/Kolkata`; timestamps must be timezone-aware. Holiday lists
must be sourced and refreshed from exchange publications. A weekday is not
necessarily a trading day, and a weekend may have a special session.

## Corporate actions

Corporate actions are essential for reliable historical analysis. The NSE
publishes corporate-action reports with ex-dates and record/book-closure dates.
A future corporate-actions module must normalize splits, bonuses, dividends,
rights, mergers and symbol/name changes. Until adjusted historical data is
available and validated, backtests must flag affected price series rather than
assume raw prices are continuous.

## Deliberately deferred

- Downloading/parsing official NSE and BSE security-master files.
- Mapping NSE tokens and BSE scrip codes from provider-specific files.
- Live holiday-file ingestion and update scheduling.
- Full corporate-action event model and adjusted-price pipeline.
- Liquidity eligibility rules and initial universe selection.

These are separate chunks so that source formats and licensing/usage conditions
can be researched and tested before adapters are implemented.
