"""Tests for header-driven NSE and BSE reference-data parsers."""

import pytest

from indian_swing_trader.instruments import Exchange, InstrumentType
from indian_swing_trader.reference_data import (
    ReferenceDataError,
    parse_bse_equity_csv,
    parse_nse_equity_csv,
)


def test_parse_nse_equity_csv_with_public_report_headers() -> None:
    source = (
        "SYMBOL,SERIES,ISIN NUMBER,NAME OF COMPANY\n"
        "RELIANCE,EQ,INE002A01018,RELIANCE INDUSTRIES LIMITED\n"
        "TCS,EQ,INE467B01029,TATA CONSULTANCY SERVICES\n"
    )

    result = parse_nse_equity_csv(source)

    assert len(result) == 2
    assert result[0].exchange is Exchange.NSE
    assert result[0].symbol == "RELIANCE"
    assert result[0].series == "EQ"
    assert result[0].isin == "INE002A01018"
    assert result[0].name == "RELIANCE INDUSTRIES LIMITED"


def test_parse_bse_equity_csv_with_standardized_identity_headers() -> None:
    source = (
        "Security Code,Security Id,Issuer Name,Group,ISIN No\n"
        "500325,RELIANCE,RELIANCE INDUSTRIES LIMITED,A,INE002A01018\n"
        "532540,TCS,TATA CONSULTANCY SERVICES,A,INE467B01029\n"
    )

    result = parse_bse_equity_csv(source)

    assert len(result) == 2
    assert result[0].exchange is Exchange.BSE
    assert result[0].symbol == "RELIANCE"
    assert result[0].security_code == "500325"
    assert result[0].series == "A"
    assert result[0].isin == "INE002A01018"


def test_parser_normalizes_header_case_and_spacing() -> None:
    source = " trading symbol , Security Series , ISIN Code\n INFY , EQ , INE009A01021\n"

    result = parse_nse_equity_csv(source)

    assert result[0].symbol == "INFY"
    assert result[0].series == "EQ"


def test_parser_supports_utf8_bom() -> None:
    source = "\ufeffSYMBOL,SERIES,ISIN\nINFY,EQ,INE009A01021\n"

    result = parse_nse_equity_csv(source)

    assert result[0].symbol == "INFY"


def test_parser_rejects_missing_required_columns() -> None:
    with pytest.raises(ReferenceDataError, match="required columns"):
        parse_nse_equity_csv("SYMBOL,ISIN\nINFY,INE009A01021\n")


def test_parser_rejects_empty_data_file() -> None:
    with pytest.raises(ReferenceDataError, match="no data rows"):
        parse_nse_equity_csv("SYMBOL,SERIES\n")


def test_parser_rejects_invalid_isin_with_row_number() -> None:
    with pytest.raises(ReferenceDataError, match="row 2"):
        parse_nse_equity_csv("SYMBOL,SERIES,ISIN\nINFY,EQ,NOT-AN-ISIN\n")


def test_parser_rejects_duplicate_exchange_identity() -> None:
    source = "SYMBOL,SERIES,ISIN\nINFY,EQ,INE009A01021\nINFY,EQ,INE009A01021\n"

    with pytest.raises(ReferenceDataError, match="duplicate instrument"):
        parse_nse_equity_csv(source)


def test_unknown_instrument_type_is_not_assumed_to_be_equity() -> None:
    source = "SYMBOL,SERIES,ISIN,INSTRUMENT TYPE\nSAMPLE,EQ,INE123A01016,UNRECOGNIZED TYPE\n"

    result = parse_nse_equity_csv(source)

    assert result[0].instrument_type is InstrumentType.OTHER
