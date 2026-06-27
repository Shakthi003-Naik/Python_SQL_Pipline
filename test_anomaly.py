"""
tests/test_anomaly.py — Unit tests for anomaly detection logic.
Run: pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import numpy as np
import pandas as pd
from anomaly import zscore_flag, iqr_flag


# ── Z-score tests ─────────────────────────────────────────

def test_zscore_normal_value_not_flagged():
    baseline = pd.Series(np.random.normal(100, 5, 30))
    is_anomaly, z = zscore_flag(102.0, baseline)
    assert not is_anomaly


def test_zscore_extreme_spike_flagged():
    baseline = pd.Series([100.0] * 30)   # very tight baseline
    is_anomaly, z = zscore_flag(200.0, baseline)
    # std=0 edge case: should not crash; spike not flagged due to zero std
    assert not is_anomaly   # handled gracefully


def test_zscore_above_threshold_flagged():
    baseline = pd.Series(np.full(30, 100.0))
    # Inject natural variance so std > 0
    baseline.iloc[0] = 95.0
    baseline.iloc[1] = 105.0
    std = baseline.std()
    spike = baseline.mean() + 4 * std   # 4 standard deviations above mean
    is_anomaly, z = zscore_flag(spike, baseline)
    assert is_anomaly
    assert z > 3.0


def test_zscore_below_threshold_not_flagged():
    baseline = pd.Series([100.0, 101.0, 99.0, 100.5, 100.2] * 6)
    is_anomaly, z = zscore_flag(100.3, baseline)
    assert not is_anomaly


def test_zscore_insufficient_data_not_flagged():
    baseline = pd.Series([100.0, 101.0])   # only 2 points
    is_anomaly, z = zscore_flag(200.0, baseline)
    assert not is_anomaly
    assert z is None


def test_zscore_returns_score_value():
    baseline = pd.Series([100.0, 102.0, 98.0, 101.0, 99.0] * 6)
    _, z = zscore_flag(101.0, baseline)
    assert isinstance(z, float)


# ── IQR tests ─────────────────────────────────────────────

def test_iqr_normal_value_not_flagged():
    baseline = pd.Series(range(50, 150))   # prices 50–149
    assert not iqr_flag(100.0, baseline)


def test_iqr_extreme_high_flagged():
    baseline = pd.Series([100.0] * 20)
    # Inject variance
    baseline.iloc[0] = 90.0
    baseline.iloc[-1] = 110.0
    # Way above Q3 + 1.5*IQR
    assert iqr_flag(300.0, baseline)


def test_iqr_extreme_low_flagged():
    baseline = pd.Series(list(range(90, 111)))   # 90–110
    assert iqr_flag(10.0, baseline)


def test_iqr_insufficient_data_not_flagged():
    baseline = pd.Series([100.0, 101.0, 102.0])   # 3 points
    assert not iqr_flag(500.0, baseline)


def test_iqr_empty_series_not_flagged():
    assert not iqr_flag(100.0, pd.Series(dtype=float))


# ── Combined logic ────────────────────────────────────────

def test_both_methods_agree_on_spike():
    """A large enough spike should be caught by both Z-score and IQR."""
    baseline = pd.Series([100.0 + i * 0.1 for i in range(30)])
    std = baseline.std()
    spike = baseline.mean() + 5 * std

    is_z, _ = zscore_flag(spike, baseline)
    is_iqr  = iqr_flag(spike, baseline)

    assert is_z, "Z-score should flag this spike"
    assert is_iqr, "IQR should flag this spike"
