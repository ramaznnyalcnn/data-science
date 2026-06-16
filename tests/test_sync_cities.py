"""Tests for scripts/sync_cities.py — cities.json ↔ CSV sync logic."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

# Import internal helpers directly (no subprocess)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.sync_cities import (
    ALL_FEATURES,
    FIZIK_FEATURES,
    SOSYAL_FEATURES,
    absorb,
    cities_to_df,
    city_json_vectors,
    report,
    vector_diffs,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_city(name: str, region: str = "r01", **feature_vals) -> dict:
    phys = {f: feature_vals.get(f, 0.10) for f in FIZIK_FEATURES}
    soc  = {f: feature_vals.get(f, 0.10) for f in SOSYAL_FEATURES}
    return {
        "id": name,
        "name": name,
        "route_id": region,
        "country": "Turkiye",
        "visa_free": True,
        "mevsim": 0,
        "physical_vector": phys,
        "sociological_vector": soc,
    }


@pytest.fixture
def two_cities():
    return [
        _make_city("CityA", deniz=0.80, doga=0.60, tarih=0.20),
        _make_city("CityB", tarih=0.90, kultur=0.85, sakin=0.40),
    ]


@pytest.fixture
def two_cities_df(two_cities):
    return cities_to_df(two_cities)


# ── city_json_vectors ─────────────────────────────────────────────────────────

def test_city_json_vectors_returns_all_features():
    city = _make_city("X", deniz=0.5)
    vecs = city_json_vectors(city)
    assert set(vecs.keys()) == set(ALL_FEATURES)


def test_city_json_vectors_correct_values():
    city = _make_city("X", deniz=0.75, tarih=0.90)
    vecs = city_json_vectors(city)
    assert abs(vecs["deniz"] - 0.75) < 1e-6
    assert abs(vecs["tarih"] - 0.90) < 1e-6


# ── cities_to_df ──────────────────────────────────────────────────────────────

def test_cities_to_df_row_count(two_cities, two_cities_df):
    assert len(two_cities_df) == len(two_cities)


def test_cities_to_df_has_required_columns(two_cities_df):
    for col in ["sehir", "region_id", "country", "visa_free"] + ALL_FEATURES + ["mevsim"]:
        assert col in two_cities_df.columns, f"Missing column: {col}"


def test_cities_to_df_feature_values(two_cities, two_cities_df):
    row_a = two_cities_df[two_cities_df["sehir"] == "CityA"].iloc[0]
    assert abs(float(row_a["deniz"]) - 0.80) < 1e-4


# ── vector_diffs ──────────────────────────────────────────────────────────────

def test_vector_diffs_no_diff():
    city = _make_city("X", deniz=0.80)
    vecs = city_json_vectors(city)
    df = cities_to_df([city])
    diffs = vector_diffs(vecs, df.iloc[0], threshold=0.05)
    assert diffs == {}


def test_vector_diffs_detects_change():
    city = _make_city("X", deniz=0.10)
    vecs = city_json_vectors(city)
    df = cities_to_df([city])
    # Manually override deniz in df row
    row = df.iloc[0].copy()
    row["deniz"] = 0.80
    diffs = vector_diffs(vecs, row, threshold=0.05)
    assert "deniz" in diffs
    assert diffs["deniz"] == (0.10, 0.80)


def test_vector_diffs_threshold():
    city = _make_city("X", deniz=0.50)
    vecs = city_json_vectors(city)
    row = cities_to_df([city]).iloc[0].copy()
    row["deniz"] = 0.53  # diff = 0.03
    assert vector_diffs(vecs, row, threshold=0.05) == {}
    assert "deniz" in vector_diffs(vecs, row, threshold=0.02)


# ── report ────────────────────────────────────────────────────────────────────

def test_report_no_issues(two_cities, two_cities_df, capsys):
    issues = report(two_cities, two_cities_df, threshold=0.05)
    assert issues == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_report_missing_city_in_csv(two_cities, capsys):
    df = cities_to_df(two_cities[:1])  # only CityA
    issues = report(two_cities, df, threshold=0.05)
    assert issues > 0
    out = capsys.readouterr().out
    assert "CityB" in out


def test_report_vector_drift(two_cities, capsys):
    df = cities_to_df(two_cities)
    df.loc[df["sehir"] == "CityA", "deniz"] = 0.99
    issues = report(two_cities, df, threshold=0.05)
    assert issues > 0
    out = capsys.readouterr().out
    assert "CityA" in out


# ── absorb ────────────────────────────────────────────────────────────────────

def test_absorb_updates_json(two_cities, tmp_path):
    cities = [c.copy() for c in two_cities]
    for c in cities:
        c["physical_vector"] = dict(c["physical_vector"])
        c["sociological_vector"] = dict(c["sociological_vector"])
    df = cities_to_df(cities)
    # Manually enrich CityA's deniz in CSV
    df.loc[df["sehir"] == "CityA", "deniz"] = 0.95

    json_path = tmp_path / "cities.json"
    json_path.write_text(json.dumps(cities, ensure_ascii=False))

    # Monkey-patch CITIES_JSON
    import scripts.sync_cities as sc
    original = sc.CITIES_JSON
    sc.CITIES_JSON = json_path
    try:
        absorb(cities, df, threshold=0.05)
    finally:
        sc.CITIES_JSON = original

    updated = json.loads(json_path.read_text())
    city_a = next(c for c in updated if c["name"] == "CityA")
    assert abs(city_a["physical_vector"]["deniz"] - 0.95) < 1e-4


# ── real data integration ─────────────────────────────────────────────────────

CITIES_JSON_PATH = Path(__file__).parent.parent / "data" / "cities.json"
CSV_PATH = Path(__file__).parent.parent / "data" / "model_destinasyonlar.csv"


@pytest.mark.skipif(not CITIES_JSON_PATH.exists() or not CSV_PATH.exists(),
                    reason="Data files not present")
def test_real_data_no_drift():
    """cities.json and model_destinasyonlar.csv must be in sync (CI gate)."""
    with open(CITIES_JSON_PATH, encoding="utf-8") as f:
        cities = json.load(f)
    df = pd.read_csv(CSV_PATH)
    issues = report(cities, df, threshold=0.05)
    assert issues == 0, "cities.json and CSV are out of sync — run: python scripts/sync_cities.py --absorb or --fix"
