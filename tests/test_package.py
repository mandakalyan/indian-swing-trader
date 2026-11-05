"""Smoke tests for the application package."""

from indian_swing_trader import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
