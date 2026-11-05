"""Tests for Indian exchange calendar primitives."""

from datetime import date, time

import pytest

from indian_swing_trader.instruments import Exchange
from indian_swing_trader.market_calendar import (
    IST,
    ExchangeCalendar,
    MarketSession,
    default_equity_session,
)


@pytest.mark.parametrize("exchange", [Exchange.NSE, Exchange.BSE])
def test_default_equity_session_uses_regular_market_hours(exchange: Exchange) -> None:
    session = default_equity_session(exchange)

    assert session.regular_open == time(9, 15)
    assert session.regular_close == time(15, 30)


def test_weekends_are_closed_by_default() -> None:
    calendar = ExchangeCalendar(exchange=Exchange.NSE)

    assert calendar.is_trading_day(date(2026, 11, 7)) is False
    assert calendar.session_for(date(2026, 11, 7)) is None


def test_configured_holiday_is_closed() -> None:
    holiday = date(2026, 11, 10)
    calendar = ExchangeCalendar(
        exchange=Exchange.NSE,
        holidays={holiday: "Exchange holiday"},
    )

    assert calendar.is_trading_day(holiday) is False
    assert calendar.holiday_reason(holiday) == "Exchange holiday"


def test_special_session_can_override_weekend_closure() -> None:
    special_day = date(2026, 11, 8)
    special = MarketSession(regular_open=time(18, 0), regular_close=time(19, 0))
    calendar = ExchangeCalendar(
        exchange=Exchange.NSE,
        holidays={special_day: "Weekend"},
        special_sessions={special_day: special},
    )

    assert calendar.is_trading_day(special_day) is True
    assert calendar.session_for(special_day) == special


def test_local_datetime_is_timezone_aware_ist() -> None:
    calendar = ExchangeCalendar(exchange=Exchange.BSE)
    result = calendar.local_datetime(date(2026, 11, 5), time(9, 15))

    assert result.tzinfo == IST
    assert result.isoformat() == "2026-11-05T09:15:00+05:30"


def test_invalid_session_times_are_rejected() -> None:
    with pytest.raises(ValueError, match="regular_open"):
        MarketSession(regular_open=time(15, 30), regular_close=time(9, 15))

    with pytest.raises(ValueError, match="pre-open"):
        MarketSession(
            regular_open=time(9, 15),
            regular_close=time(15, 30),
            pre_open_start=time(9, 10),
        )
