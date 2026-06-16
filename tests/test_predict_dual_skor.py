"""Tests for model/predict.py — dual_skor and weighted_cosine."""

import numpy as np
import pandas as pd
import pytest

from model.predict import dual_skor, oneri_yap, weighted_cosine
from model.config import FIZIK_FEATURES, SOSYAL_FEATURES, FIZIK_WEIGHTS, SOSYAL_WEIGHTS, MEVSIM_CARPAN

W_FIZ = np.array([FIZIK_WEIGHTS[f] for f in FIZIK_FEATURES], dtype=float)
W_SOS = np.array([SOSYAL_WEIGHTS[f] for f in SOSYAL_FEATURES], dtype=float)

N_FIZ = len(FIZIK_FEATURES)
N_SOS = len(SOSYAL_FEATURES)


def zero_fiz():
    return np.zeros(N_FIZ)


def zero_sos():
    return np.zeros(N_SOS)


def ones_fiz():
    return np.ones(N_FIZ)


def ones_sos():
    return np.ones(N_SOS)


# ── weighted_cosine ────────────────────────────────────────

def test_weighted_cosine_identical_vectors_is_one():
    v = np.array([0.5, 0.3, 0.8])
    W = np.ones(3)
    assert weighted_cosine(v, v, W) == pytest.approx(1.0, abs=1e-6)


def test_weighted_cosine_zero_vector_returns_zero():
    v = np.array([0.5, 0.3, 0.8])
    z = np.zeros(3)
    W = np.ones(3)
    assert weighted_cosine(v, z, W) == 0.0
    assert weighted_cosine(z, v, W) == 0.0


def test_weighted_cosine_orthogonal_is_zero():
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    W = np.ones(3)
    assert weighted_cosine(a, b, W) == pytest.approx(0.0, abs=1e-6)


# ── dual_skor ─────────────────────────────────────────────

def test_dual_skor_zero_user_returns_zero():
    toplam, skor_fiz, skor_sos = dual_skor(zero_fiz(), zero_sos(), ones_fiz(), ones_sos())
    assert toplam == 0.0
    assert skor_fiz == 0.0
    assert skor_sos == 0.0


def test_dual_skor_identical_returns_near_one():
    u_fiz = np.random.rand(N_FIZ)
    u_sos = np.random.rand(N_SOS)
    toplam, _, _ = dual_skor(u_fiz, u_sos, u_fiz, u_sos)
    assert toplam > 0.9


def test_dual_skor_returns_three_values():
    result = dual_skor(ones_fiz(), ones_sos(), ones_fiz(), ones_sos())
    assert len(result) == 3


def test_dual_skor_season_penalty_reduces_score():
    u_fiz = ones_fiz()
    u_sos = ones_sos()
    s_fiz = ones_fiz()
    s_sos = ones_sos()
    # Mevsim uyumlu (u=0 yaz, s=0 yaz) — ceza yok
    toplam_match, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim=0, u_mevsim=0)
    # Mevsim uyumsuz (u=0 yaz, s=1 kış) — ceza var
    toplam_mismatch, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim=1, u_mevsim=0)
    assert toplam_mismatch < toplam_match


def test_dual_skor_no_season_penalty_when_year_round():
    u_fiz = ones_fiz()
    u_sos = ones_sos()
    s_fiz = ones_fiz()
    s_sos = ones_sos()
    # s_mevsim=2 (yıl boyu) → ceza uygulanmaz
    toplam_yr, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim=2, u_mevsim=0)
    toplam_match, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim=0, u_mevsim=0)
    assert toplam_yr == pytest.approx(toplam_match, abs=1e-6)


def test_dual_skor_scores_are_non_negative():
    u_fiz = np.random.rand(N_FIZ)
    u_sos = np.random.rand(N_SOS)
    s_fiz = np.random.rand(N_FIZ)
    s_sos = np.random.rand(N_SOS)
    toplam, skor_fiz, skor_sos = dual_skor(u_fiz, u_sos, s_fiz, s_sos)
    assert toplam >= 0.0
    assert skor_fiz >= 0.0
    assert skor_sos >= 0.0


# ── oneri_yap shuffle ─────────────────────────────────────

def _city_row(name, deniz, doga, eglence, sakin):
    row = {
        "sehir": name,
        "mevsim": 2,
    }
    for feature in FIZIK_FEATURES:
        row[feature] = 0.0
    for feature in SOSYAL_FEATURES:
        row[feature] = 0.0
    row["deniz"] = deniz
    row["doga"] = doga
    row["eglence"] = eglence
    row["sakin"] = sakin
    return row


def _recommendation_df():
    return pd.DataFrame([
        _city_row("A", deniz=1.0, doga=0.8, eglence=1.0, sakin=0.2),
        _city_row("B", deniz=0.7, doga=0.4, eglence=0.7, sakin=0.2),
        _city_row("C", deniz=0.2, doga=0.1, eglence=0.2, sakin=0.2),
    ])


def test_oneri_yap_shuffle_false_keeps_rank_order():
    u_fiz = np.zeros(N_FIZ)
    u_sos = np.zeros(N_SOS)
    u_fiz[FIZIK_FEATURES.index("deniz")] = 1.0
    u_fiz[FIZIK_FEATURES.index("doga")] = 0.8
    u_sos[SOSYAL_FEATURES.index("eglence")] = 1.0

    result = oneri_yap(u_fiz, u_sos, _recommendation_df(), top_n=3, shuffle=False)

    assert [item["sehir"] for item in result] == ["A", "B", "C"]


def test_oneri_yap_shuffle_true_keeps_same_items(monkeypatch):
    u_fiz = np.zeros(N_FIZ)
    u_sos = np.zeros(N_SOS)
    u_fiz[FIZIK_FEATURES.index("deniz")] = 1.0
    u_fiz[FIZIK_FEATURES.index("doga")] = 0.8
    u_sos[SOSYAL_FEATURES.index("eglence")] = 1.0

    import model.predict as predict_module

    monkeypatch.setattr(predict_module.random, "shuffle", lambda values: values.reverse())
    ranked = oneri_yap(u_fiz, u_sos, _recommendation_df(), top_n=3, shuffle=False)
    shuffled = oneri_yap(u_fiz, u_sos, _recommendation_df(), top_n=3, shuffle=True)

    assert {item["sehir"] for item in shuffled} == {item["sehir"] for item in ranked}
    assert [item["sehir"] for item in shuffled] == list(reversed([item["sehir"] for item in ranked]))

