"""
tests/test_transform.py — Unit tests for the transform module.
Run: pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import pandas as pd
from transform import transform


# ── Fixtures ──────────────────────────────────────────────

def make_row(**overrides) -> dict:
    """Return a valid raw row, with optional field overrides."""
    row = {
        "symbol":      "AAPL",
        "trade_date":  "2024-01-15",
        "open_price":  "185.0000",
        "high_price":  "188.4400",
        "low_price":   "184.3500",
        "close_price": "187.1500",
        "volume":      "55234100",
    }
    row.update(overrides)
    return row


# ── Happy path ────────────────────────────────────────────

def test_valid_rows_pass_through():
    rows = [make_row(), make_row(trade_date="2024-01-16", close_price="190.0")]
    df = transform(rows)
    assert len(df) == 2
    assert list(df.columns[:2]) == ["symbol", "trade_date"]


def test_prices_are_floats():
    df = transform([make_row()])
    assert df["close_price"].dtype == float
    assert df["open_price"].dtype == float


def test_volume_is_integer():
    df = transform([make_row()])
    assert pd.api.types.is_integer_dtype(df["volume"])


def test_trade_date_is_datetime():
    df = transform([make_row()])
    assert pd.api.types.is_datetime64_any_dtype(df["trade_date"])


def test_prices_rounded_to_4dp():
    df = transform([make_row(close_price="187.123456789")])
    assert df["close_price"].iloc[0] == round(187.123456789, 4)


# ── Validation — dropped rows ─────────────────────────────

def test_negative_price_dropped():
    df = transform([make_row(close_price="-5.0")])
    assert df.empty


def test_zero_price_dropped():
    df = transform([make_row(open_price="0")])
    assert df.empty


def test_invalid_date_dropped():
    df = transform([make_row(trade_date="not-a-date")])
    assert df.empty


def test_invalid_volume_dropped():
    df = transform([make_row(volume="abc")])
    assert df.empty


def test_price_inconsistency_dropped():
    # low > high — violates OHLC rules
    df = transform([make_row(low_price="200.0", high_price="150.0")])
    assert df.empty


# ── Deduplication ─────────────────────────────────────────

def test_duplicates_removed():
    rows = [make_row(), make_row()]   # same symbol + date
    df = transform(rows)
    assert len(df) == 1


# ── Edge cases ────────────────────────────────────────────

def test_empty_input_returns_empty_df():
    df = transform([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_mixed_valid_invalid():
    rows = [
        make_row(),                           # valid
        make_row(close_price="-1"),           # invalid: negative
        make_row(trade_date="2024-01-17"),    # valid
    ]
    df = transform(rows)
    assert len(df) == 2
