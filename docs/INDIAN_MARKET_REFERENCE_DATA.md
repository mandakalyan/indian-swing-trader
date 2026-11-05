# Indian Market Reference Data

## Scope

Both NSE and BSE are supported at the instrument identity level. Initial screening
may prioritize NSE. Exchange-specific identifiers and series are preserved.

Canonical listing identity is `(exchange, symbol, series)`. ISIN is retained as
a cross-market identifier when supplied, not used as the only primary key.
Exchange security codes/tokens remain provider or exchange identifiers.

## Official sources reviewed

- NSE Securities available for trading publishes separate equity, SME, ETF,
  preference-share, warrant, debt, symbol-change and company-name-change files:
  https://www.nseindia.com/static/market-data/securities-available-for-trading
- NSE market reports describe its securities master as containing symbol, ISIN,
  security code and series:
  https://www.nseindia.com/static/products-services/equity-market-data-reports-download
- NSE master-data specification documents the member-facing NEAT capital-market
  `security.txt` format as gzip-compressed, pipe-delimited records with a header
  followed by data records. It includes token, symbol, series and instrument type:
  https://nsearchives.nseindia.com/web/sites/default/files/inline-files/NSE-Masters%20Data-v1.6.pdf
- NSE's UDiFF documentation is separately versioned and provides CM trade and
  bhavcopy formats. It is not interchangeable with the member security master:
  https://www.nseindia.com/static/resources/forms-formats-members
- NSE circular MSD67344 describes daily security-master dissemination and
  distinguishes NSE-only and combined NSE/BSE-listed security files:
  https://nsearchives.nseindia.com/content/circulars/MSD67344.pdf
- BSE publishes a Standardised Security Master file specification and related
  exchange circulars. The format is wide and versioned:
  https://www.bseindia.com/markets/MarketInfo/DownloadAttach.aspx?attachedId=e99e2ca5-95d7-4173-83da-7774412bbb2d&id=20220531-44
- BSE's 2026 circular changes the standardized scrip master, including the
  Closing Auction Session indicator in field 24 and an ISO tag change in field 59,
  effective 31 July 2026:
  https://www.bseindia.com/markets/MarketInfo/DownloadAttach.aspx?attachedId=8a7fec3a-95bc-4bd2-82de-76e2a84e2915&id=20250429-51

## Parser design implemented

The first ingestion increment provides header-driven CSV parsers:

- `parse_nse_equity_csv` accepts public header-based NSE equity securities CSV
  layouts with recognized symbol and series columns.
- `parse_bse_equity_csv` accepts recognized BSE standardized equity scrip-master
  identity columns.
- Both parsers normalize header spelling/case, preserve exchange identity,
  reject missing required columns, invalid identifiers and duplicate identities.
- Unrecognized columns are ignored; they are not guessed or mapped by position.
- An unknown instrument-type label maps to OTHER, never silently to EQUITY.

These parsers do not yet parse the member-facing pipe-delimited NEAT security.gz
file, all versions of the NSE MII security file, or every BSE historical/binary
format. Those need explicit format versions and real sample fixtures before
implementation. Do not point a parser at an arbitrary exchange file and assume
it is compatible.

## Operational requirements for the ingestion service

A future downloader/ingestion job must:

1. Use an approved official source URL and record the exact source URL.
2. Record retrieval time, source file date, content hash, parser name and parser
   version.
3. Download to a temporary file, validate the complete file, then publish the
   resulting snapshot atomically.
4. Keep the last-known-good snapshot if a new file is malformed or incomplete.
5. Report row counts, rejected rows, duplicate identities and unexpected schema
   changes; fail rather than silently publishing a partial universe.
6. Preserve source files or a reproducible checksum/reference for audit and
   debugging.
7. Avoid hard-coded undocumented endpoints and do not bypass exchange access
   controls or terms of use.

## Deliberately deferred

- Live downloading and refresh scheduling.
- Parsing NSE pipe-delimited NEAT security.gz and versioned MII/UDiFF files.
- Full BSE field-by-field standardized master mapping and schema-version registry.
- Mapping broker-specific instrument tokens.
- Security lifecycle history (symbol changes, suspensions, delistings).
- Corporate-action events and adjusted historical price series.
- Database persistence and snapshot-diff reports.

These are separate increments because exchange formats evolve. A parser should
only be declared production-ready after it has been tested against a real,
dated, official sample file for the exact format version it supports.
