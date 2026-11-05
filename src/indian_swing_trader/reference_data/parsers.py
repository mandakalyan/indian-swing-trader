"""Header-driven parsers for public NSE and BSE equity reference CSVs.

Exchange download layouts can evolve. These parsers resolve known column names
from the header instead of depending on fragile fixed column positions. They
fail closed when required identifiers are absent or rows are malformed.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Mapping
from typing import TextIO

from indian_swing_trader.instruments import Exchange, Instrument, InstrumentType


class ReferenceDataError(ValueError):
    """Raised when an exchange reference file cannot be safely interpreted."""


def _normalise_header(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.strip().upper())


def _resolve_columns(
    headers: Iterable[str],
    aliases: Mapping[str, tuple[str, ...]],
    required: tuple[str, ...],
) -> dict[str, str]:
    available = {_normalise_header(header): header for header in headers}
    resolved: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            match = available.get(_normalise_header(candidate))
            if match is not None:
                resolved[canonical] = match
                break
    missing = [field for field in required if field not in resolved]
    if missing:
        raise ReferenceDataError(
            "reference file is missing required columns: " + ", ".join(missing)
        )
    return resolved


def _instrument_type(raw: str | None) -> InstrumentType:
    if not raw:
        return InstrumentType.EQUITY
    value = raw.strip().upper()
    mapping = {
        "EQUITY": InstrumentType.EQUITY,
        "EQ": InstrumentType.EQUITY,
        "ETF": InstrumentType.ETF,
        "REIT": InstrumentType.REIT,
        "INVIT": InstrumentType.INVIT,
        "PREFERENCE": InstrumentType.PREFERENCE_SHARE,
        "PREFERENCE SHARE": InstrumentType.PREFERENCE_SHARE,
        "DEBENTURE": InstrumentType.DEBT,
        "DEBT": InstrumentType.DEBT,
        "WARRANT": InstrumentType.WARRANT,
    }
    return mapping.get(value, InstrumentType.OTHER)


def _read_csv(source: str | TextIO) -> list[dict[str, str]]:
    stream = io.StringIO(source, newline="") if isinstance(source, str) else source
    try:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ReferenceDataError("reference CSV has no header row")
        rows = list(reader)
    except csv.Error as exc:
        raise ReferenceDataError(f"invalid CSV: {exc}") from exc
    if not rows:
        raise ReferenceDataError("reference CSV contains no data rows")
    return rows


def _parse_rows(
    source: str | TextIO,
    *,
    exchange: Exchange,
    aliases: Mapping[str, tuple[str, ...]],
    required: tuple[str, ...],
) -> list[Instrument]:
    rows = _read_csv(source)
    columns = _resolve_columns(rows[0].keys(), aliases, required)
    instruments: list[Instrument] = []
    seen: set[tuple[Exchange, str, str | None]] = set()

    for line_number, row in enumerate(rows, start=2):
        def value(field: str) -> str | None:
            column = columns.get(field)
            if column is None:
                return None
            raw = row.get(column)
            if raw is None:
                return None
            cleaned = raw.strip()
            return cleaned or None

        symbol = value("symbol")
        series = value("series")
        isin = value("isin")
        code = value("security_code")
        name = value("name")
        type_value = value("instrument_type")

        if not symbol:
            raise ReferenceDataError(f"row {line_number}: missing symbol/security id")
        try:
            instrument = Instrument(
                exchange=exchange,
                symbol=symbol,
                series=series,
                isin=isin,
                security_code=code,
                name=name,
                instrument_type=_instrument_type(type_value),
            )
        except ValueError as exc:
            raise ReferenceDataError(f"row {line_number}: {exc}") from exc

        if instrument.identity in seen:
            raise ReferenceDataError(
                f"row {line_number}: duplicate instrument identity {instrument.identity}"
            )
        seen.add(instrument.identity)
        instruments.append(instrument)

    return instruments


_NSE_ALIASES = {
    "symbol": ("SYMBOL", "TRADING SYMBOL", "SECURITY SYMBOL"),
    "series": ("SERIES", "SECURITY SERIES"),
    "isin": ("ISIN NUMBER", "ISIN", "ISIN CODE"),
    "security_code": ("SECURITY CODE", "TOKEN", "INSTRUMENT TOKEN"),
    "name": ("NAME OF COMPANY", "COMPANY NAME", "SECURITY NAME"),
    "instrument_type": ("INSTRUMENT TYPE", "TYPE"),
}

_BSE_ALIASES = {
    "symbol": ("SECURITY ID", "SCRIP ID", "TRADING SYMBOL", "SYMBOL"),
    "series": ("GROUP", "SCRIP GROUP", "SERIES"),
    "isin": ("ISIN NO", "ISIN NUMBER", "ISIN"),
    "security_code": ("SECURITY CODE", "SCRIP CODE", "SC CODE"),
    "name": ("ISSUER NAME", "SECURITY NAME", "COMPANY NAME"),
    "instrument_type": ("INSTRUMENT TYPE", "TYPE"),
}


def parse_nse_equity_csv(source: str | TextIO) -> list[Instrument]:
    """Parse an NSE equity securities CSV with recognized header names.

    This parser targets the public, header-based equity securities listings.
    It does not parse the separate pipe-delimited NEAT member security.gz file
    or every UDiFF report; those formats need distinct versioned parsers.
    """

    return _parse_rows(
        source,
        exchange=Exchange.NSE,
        aliases=_NSE_ALIASES,
        required=("symbol", "series"),
    )


def parse_bse_equity_csv(source: str | TextIO) -> list[Instrument]:
    """Parse a BSE standardized equity scrip-master CSV.

    BSE's standardized file is wide and versioned. Only stable identity fields
    are consumed here; unrecognized columns are intentionally ignored.
    """

    return _parse_rows(
        source,
        exchange=Exchange.BSE,
        aliases=_BSE_ALIASES,
        required=("symbol", "security_code"),
    )
