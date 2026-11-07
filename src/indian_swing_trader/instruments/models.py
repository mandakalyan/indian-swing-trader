"""Canonical instrument models for Indian listed markets.

The model deliberately preserves exchange-specific identifiers and series. A
company's ISIN can be shared across exchange listings, while its exchange symbol
and series are not assumed to be globally unique.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import re


_ISIN_PATTERN = re.compile(r"^IN[A-Z0-9]{10}$")
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&._-]+$")


class Exchange(StrEnum):
    """Supported Indian equity exchanges."""

    NSE = "NSE"
    BSE = "BSE"


class InstrumentType(StrEnum):
    """Broad instrument classifications used by the research system."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    REIT = "REIT"
    INVIT = "INVIT"
    PREFERENCE_SHARE = "PREFERENCE_SHARE"
    DEBT = "DEBT"
    WARRANT = "WARRANT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Instrument:
    """A listed instrument as identified on one exchange.

    `symbol` and `series` are exchange-specific values. ISIN is optional because
    some exchange/reference records may not supply one. `security_code` stores
    the exchange's own numeric or textual identifier without coercing it.
    """

    exchange: Exchange
    symbol: str
    series: str | None = None
    isin: str | None = None
    security_code: str | None = None
    name: str | None = None
    instrument_type: InstrumentType = InstrumentType.EQUITY
    active: bool = True
    tick_size: Decimal | None = None
    lot_size: int | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol or not _SYMBOL_PATTERN.fullmatch(symbol):
            raise ValueError("symbol must contain only letters, digits, &, ., _, or -")
        object.__setattr__(self, "symbol", symbol)

        if self.series is not None:
            series = self.series.strip().upper()
            if not series:
                raise ValueError("series cannot be empty when supplied")
            object.__setattr__(self, "series", series)

        if self.isin is not None:
            isin = self.isin.strip().upper()
            if not _ISIN_PATTERN.fullmatch(isin):
                raise ValueError("ISIN must be 12 characters and start with IN")
            object.__setattr__(self, "isin", isin)

        if self.security_code is not None:
            code = str(self.security_code).strip()
            if not code:
                raise ValueError("security_code cannot be empty when supplied")
            object.__setattr__(self, "security_code", code)

        if self.name is not None:
            name = self.name.strip()
            if not name:
                raise ValueError("name cannot be empty when supplied")
            object.__setattr__(self, "name", name)

        if self.tick_size is not None and self.tick_size <= Decimal("0"):
            raise ValueError("tick_size must be greater than zero")

        if self.lot_size is not None and self.lot_size <= 0:
            raise ValueError("lot_size must be greater than zero")

    @property
    def identity(self) -> tuple[Exchange, str, str | None]:
        """Return the exchange-scoped identity (exchange, symbol, series)."""

        return (self.exchange, self.symbol, self.series)
