"""Vector quality sentinels for model_destinasyonlar.csv.

Each city must have at least MIN_FEATURES_ABOVE features >= MIN_THRESHOLD.
Key destinations are tested for expected high values.
"""
from pathlib import Path

import pandas as pd
import pytest

DATA_PATH = Path(__file__).parent.parent / "data" / "model_destinasyonlar.csv"

FIZIK_FEATURES = ["deniz", "doga", "tarih", "kultur", "doga_spor", "su_spor", "hava_spor", "kis_spor"]
SOSYAL_FEATURES = ["eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat"]
ALL_FEATURES = FIZIK_FEATURES + SOSYAL_FEATURES

MIN_THRESHOLD = 0.30
MIN_FEATURES_ABOVE = 3


@pytest.fixture(scope="module")
def df():
    if not DATA_PATH.exists():
        pytest.skip(f"CSV not found: {DATA_PATH}")
    return pd.read_csv(DATA_PATH)


def test_csv_loads_with_rows(df):
    assert len(df) > 0, "model_destinasyonlar.csv is empty"


def test_sehir_column_exists(df):
    assert "sehir" in df.columns


def test_each_city_has_enough_notable_features(df):
    """Each city must have >= 3 features above 0.30 (Faz D data quality gate)."""
    available = [f for f in ALL_FEATURES if f in df.columns]
    failing = []
    for _, row in df.iterrows():
        vals = [float(row[f]) for f in available]
        n_above = sum(v >= MIN_THRESHOLD for v in vals)
        if n_above < MIN_FEATURES_ABOVE:
            failing.append(
                f"{row['sehir']}: {n_above} features >= {MIN_THRESHOLD} "
                f"(need {MIN_FEATURES_ABOVE})"
            )
    if failing:
        msg = f"{len(failing)} cities with too few notable features:\n" + "\n".join(failing[:15])
        if len(failing) > 15:
            msg += f"\n... and {len(failing) - 15} more"
        pytest.fail(msg)


def test_sentinel_kapadokya_tarih(df):
    row = df[df["sehir"].str.lower().str.contains("kapadokya", na=False)]
    if row.empty:
        pytest.skip("Kapadokya not in dataset")
    if "tarih" in df.columns:
        assert float(row.iloc[0]["tarih"]) >= 0.50, "Kapadokya tarih too low"


def test_sentinel_istanbul_kultur(df):
    row = df[df["sehir"].str.lower().str.contains("istanbul", na=False)]
    if row.empty:
        pytest.skip("Istanbul not in dataset")
    if "kultur" in df.columns:
        assert float(row.iloc[0]["kultur"]) >= 0.50, "Istanbul kultur too low"


def test_no_all_zero_city(df):
    available = [f for f in ALL_FEATURES if f in df.columns]
    zero_cities = []
    for _, row in df.iterrows():
        vals = [float(row[f]) for f in available]
        if all(v < 0.01 for v in vals):
            zero_cities.append(row["sehir"])
    assert not zero_cities, f"Cities with all-zero feature vectors: {zero_cities}"


def test_feature_range_zero_to_one(df):
    available = [f for f in ALL_FEATURES if f in df.columns]
    for col in available:
        assert df[col].min() >= 0.0, f"{col} has negative values"
        assert df[col].max() <= 1.0, f"{col} has values > 1.0"
