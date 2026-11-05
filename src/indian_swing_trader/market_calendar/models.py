"""Timezone-aware exchange calendar primitives.

Holiday dates are injected as reference data; this package does not pretend that
a hard-coded holiday list is authoritative or permanently current.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo

from indian_swing_trader.instruments.models import Exchange

IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True, slots=True)
class MarketSession:
    """Trading-session times expressed as local exchange wall-clock times."""

    regular_open: time
    regular_close: time
    pre_open_start: time | None = None
    pre_open_end: time | None = None

    def __post_init__(self) -> None:
        if self.regular_open >= self.regular_close:
            raise ValueError("regular_open must be earlier than regular_close")
        if (self.pre_open_start is None) != (self.pre_open_end is None):
            raise ValueError("pre-open start and end must either both be set or both be absent")
        if self.pre_open_start is not None and self.pre_open_end is not None:
            if self.pre_open_start >= self.pre_open_end:
                raise ValueError("pre-open start must be earlier than pre-open end")


@dataclass(frozen=True, slots=True)
class ExchangeCalendar:
    """Calendar for one exchange, with explicit holiday and special-session data."""

    exchange: Exchange
    holidays: Mapping[date, str] = field(default_factory=dict)
    special_sessions: Mapping[date, MarketSession] = field(default_factory=dict)
    regular_session: MarketSession = field(
        default_factory=lambda: default_equity_session(Exchange.NSE)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "holidays", MappingProxyType(dict(self.holidays)))
        object.__setattr__(
            self, "special_sessions", MappingProxyType(dict(self.special_sessions))
        )

    def is_trading_day(self, day: date) -> bool:
        """Return whether a date has a configured trading session."""

        if day in self.special_sessions:
            return True
        if day in self.holidays:
            return False
        return day.weekday() < 5

    def session_for(self, day: date) -> MarketSession | None:
        """Return the session for a date, or None when the exchange is closed."""

        if day in self.special_sessions:
            return self.special_sessions[day]
        if not self.is_trading_day(day):
            return None
        return self.regular_session

    def holiday_reason(self, day: date) -> str | None:
        """Return the configured holiday description, if present."""

        return self.holidays.get(day)

    def local_datetime(self, day: date, at: time) -> datetime:
        """Combine a date and exchange wall-clock time using Asia/Kolkata."""

        return datetime.combine(day, at, tzinfo=IST)


def default_equity_session(exchange: Exchange) -> MarketSession:
    """Return the regular continuous equity session for NSE or BSE.

    Both exchanges publish a 09:15–15:30 continuous equity session. Their
    pre-open procedures and special sessions are not identical, so no common
    pre-open interval is assumed here.
    """

    if exchange not in (Exchange.NSE, Exchange.BSE):
        raise ValueError(f"unsupported exchange: {exchange}")
    return MarketSession(regular_open=time(9, 15), regular_close=time(15, 30))
