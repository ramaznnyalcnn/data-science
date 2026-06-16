"""Smoke tests for synthetic evaluation helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).parent.parent / "notebooks" / "01_synthetic_eval.py"
spec = importlib.util.spec_from_file_location("synthetic_eval", MODULE_PATH)
synthetic_eval = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(synthetic_eval)


def _tiny_df() -> pd.DataFrame:
    rows = []
    for name, deniz, doga, eglence in [
        ("A", 1.0, 0.2, 0.9),
        ("B", 0.2, 1.0, 0.2),
        ("C", 0.1, 0.2, 0.1),
    ]:
        row = {"sehir": name, "mevsim": 2}
        for feature in synthetic_eval.FIZIK_FEATURES:
            row[feature] = 0.0
        for feature in synthetic_eval.SOSYAL_FEATURES:
            row[feature] = 0.0
        row["deniz"] = deniz
        row["doga"] = doga
        row["eglence"] = eglence
        rows.append(row)
    return pd.DataFrame(rows)


def test_persona_vector_is_8_plus_5():
    u_fiz, u_sos = synthetic_eval.persona_vektor(
        {"deniz": 1.0, "eglence": 0.8},
        gurultu=0.0,
    )
    assert len(u_fiz) == 8
    assert len(u_sos) == 5


def test_ranking_metrics_are_bounded():
    truth = {"A", "B"}
    assert 0.0 <= synthetic_eval.ndcg_at_k(["A", "C", "B"], truth, 3) <= 1.0
    assert synthetic_eval.hit_at_k(["C", "B"], truth, 2) == 1.0


def test_display_ablation_returns_expected_metrics():
    metrics = synthetic_eval.ablation_sorted_vs_shuffled_display(_tiny_df(), n_per_persona=1)
    expected = {
        "Sorted NDCG@3",
        "Shuffled display NDCG@3",
        "Sorted shown-position proxy",
        "Shuffled shown-position proxy",
    }
    assert set(metrics) == expected
    assert all(isinstance(value, float) for value in metrics.values())


def test_dual_vs_flat_ablation_returns_expected_metrics():
    metrics = synthetic_eval.ablation_dual_vs_flat(_tiny_df())
    expected = {
        "Flat 13 NDCG@3",
        "Flat 13 Hit@3",
        "Dual 8+5 NDCG@3",
        "Dual 8+5 Hit@3",
        "NDCG Delta",
    }
    assert set(metrics) == expected
