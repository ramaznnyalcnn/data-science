"""Tests for the active recommendation facade."""

from __future__ import annotations

import numpy as np
import pandas as pd

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES
from model.recommend import candidate_pool_for_regions, load_ranker, recommend_places


def _row(name: str, region_id: str, deniz: float = 0.0, sakin: float = 0.0) -> dict:
    row = {"sehir": name, "region_id": region_id, "mevsim": 2}
    for feature in FIZIK_FEATURES:
        row[feature] = 0.0
    for feature in SOSYAL_FEATURES:
        row[feature] = 0.0
    row["deniz"] = deniz
    row["sakin"] = sakin
    return row


def test_candidate_pool_for_regions_filters_selected_region_ids():
    df = pd.DataFrame([
        _row("A", "region_1", sakin=0.8),
        _row("B", "region_2", sakin=0.3),
        _row("C", "region_1", sakin=0.6),
    ])
    user_sos = np.zeros(len(SOSYAL_FEATURES))
    user_sos[SOSYAL_FEATURES.index("sakin")] = 1.0

    result = candidate_pool_for_regions(df, ["region_1"], user_sos)

    assert set(result["region_id"]) == {"region_1"}
    assert list(result["sehir"]) == ["A", "C"]


def test_candidate_pool_for_regions_falls_back_when_region_empty():
    df = pd.DataFrame([
        _row("A", "region_1"),
        _row("B", "region_2"),
    ])

    result = candidate_pool_for_regions(df, ["missing_region"])

    assert set(result["sehir"]) == {"A", "B"}


def test_load_ranker_missing_artifact_returns_none(tmp_path):
    assert load_ranker(tmp_path / "missing.joblib") is None


def test_recommend_places_uses_hybrid_fallback_without_model():
    df = pd.DataFrame([
        _row("Sea", "region_1", deniz=1.0),
        _row("Other", "region_1", deniz=0.1),
    ])
    u_fiz = np.zeros(len(FIZIK_FEATURES))
    u_sos = np.zeros(len(SOSYAL_FEATURES))
    u_fiz[FIZIK_FEATURES.index("deniz")] = 1.0

    result = recommend_places(u_fiz, u_sos, df, top_n=2, model=None)

    assert [item["sehir"] for item in result] == ["Sea", "Other"]
