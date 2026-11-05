"""Tests for canonical instrument reference models."""

from decimal import Decimal

import pytest

from indian_swing_trader.instruments import Exchange, Instrument, InstrumentType


def test_instrument_normalizes_exchange_symbol_and_isin() -> None:
    instrument = Instrument(
        exchange=Exchange.NSE,
        symbol=" reliance ",
        series=" eq ",
        isin=" INE002A01018 ",
    )

    assert instrument.symbol == "RELIANCE"
    assert instrument.series == "EQ"
    assert instrument.isin == "INE002A01018"
    assert instrument.identity == (Exchange.NSE, "RELIANCE", "EQ")


def test_same_company_on_two_exchanges_has_distinct_identity() -> None:
    nse = Instrument(exchange=Exchange.NSE, symbol="RELIANCE", isin="INE002A01018")
    bse = Instrument(exchange=Exchange.BSE, symbol="500325", isin="INE002A01018")

    assert nse.isin == bse.isin
    assert nse.identity != bse.identity


@pytest.mark.parametrize("isin", ["", "US0378331005", "INE002A0101", "INE002A0101!"])
def test_invalid_isin_is_rejected(isin: str) -> None:
    with pytest.raises(ValueError, match="ISIN"):
        Instrument(exchange=Exchange.NSE, symbol="RELIANCE", isin=isin)


@pytest.mark.parametrize("symbol", ["", "RELIANCE LTD", "RELIANCE/ EQ"])
def test_invalid_symbol_is_rejected(symbol: str) -> None:
    with pytest.raises(ValueError, match="symbol"):
        Instrument(exchange=Exchange.NSE, symbol=symbol)


def test_tick_size_and_lot_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="tick_size"):
        Instrument(exchange=Exchange.NSE, symbol="ABC", tick_size=Decimal("0"))

    with pytest.raises(ValueError, match="lot_size"):
        Instrument(exchange=Exchange.NSE, symbol="ABC", lot_size=0)


def test_instrument_type_is_explicit() -> None:
    instrument = Instrument(
        exchange=Exchange.BSE,
        symbol="EXAMPLE",
        instrument_type=InstrumentType.ETF,
    )

    assert instrument.instrument_type is InstrumentType.ETF
