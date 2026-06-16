"""Tests for model/scope_filter.py."""

import pandas as pd
import pytest

from model.scope_filter import (
    SCOPE_ABROAD,
    SCOPE_MIXED,
    SCOPE_TURKEY,
    VISA_FREE,
    VISA_INCLUDE_REQUIRED,
    filter_destinations,
    needs_visa_filter,
)


@pytest.fixture()
def sample_df():
    return pd.DataFrame([
        {"sehir": "Istanbul",  "country": "Turkiye",  "visa_free": True},
        {"sehir": "Antalya",   "country": "Turkiye",  "visa_free": True},
        {"sehir": "Paris",     "country": "France",   "visa_free": True},
        {"sehir": "Moskova",   "country": "Russia",   "visa_free": False},
    ])


def test_scope_turkey_returns_only_turkey(sample_df):
    result = filter_destinations(sample_df, scope_mode=SCOPE_TURKEY, visa_mode=VISA_FREE)
    assert set(result["country"]) == {"Turkiye"}


def test_scope_abroad_excludes_turkey(sample_df):
    result = filter_destinations(sample_df, scope_mode=SCOPE_ABROAD, visa_mode=VISA_FREE)
    assert "Turkiye" not in result["country"].values


def test_scope_mixed_includes_all(sample_df):
    result = filter_destinations(sample_df, scope_mode=SCOPE_MIXED, visa_mode=VISA_INCLUDE_REQUIRED)
    assert len(result) == 4


def test_visa_free_excludes_visa_required_foreign(sample_df):
    result = filter_destinations(sample_df, scope_mode=SCOPE_MIXED, visa_mode=VISA_FREE)
    assert "Moskova" not in result["sehir"].values


def test_visa_include_required_keeps_all(sample_df):
    result = filter_destinations(sample_df, scope_mode=SCOPE_MIXED, visa_mode=VISA_INCLUDE_REQUIRED)
    assert "Moskova" in result["sehir"].values


def test_empty_df_returns_empty(sample_df):
    empty = sample_df.iloc[:0]
    result = filter_destinations(empty, scope_mode=SCOPE_TURKEY, visa_mode=VISA_FREE)
    assert result.empty


def test_unknown_scope_mode_raises(sample_df):
    with pytest.raises(ValueError):
        filter_destinations(sample_df, scope_mode="invalid_mode", visa_mode=VISA_FREE)


def test_needs_visa_filter_turkey_scope_is_false(sample_df):
    assert needs_visa_filter(sample_df, SCOPE_TURKEY) is False


def test_needs_visa_filter_abroad_scope_is_true(sample_df):
    assert needs_visa_filter(sample_df, SCOPE_ABROAD) is True
