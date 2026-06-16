"""Tests for Streamlit UI HTML helpers."""

from __future__ import annotations

import numpy as np

from app.utils import _preference_vector_html
from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


def test_preference_vector_html_groups_physical_and_social_features():
    fizik = np.linspace(0.1, 0.8, len(FIZIK_FEATURES))
    sosyal = np.linspace(0.2, 0.6, len(SOSYAL_FEATURES))

    html = _preference_vector_html(fizik, sosyal, "TR")

    assert "Rota / görsel tercihler" in html
    assert "Sosyal / pratik tercihler" in html
    assert "Deniz" in html
    assert "Eğlence" in html
    assert html.count("feat-row") == len(FIZIK_FEATURES) + len(SOSYAL_FEATURES)


def test_preference_vector_html_supports_english_labels():
    fizik = np.zeros(len(FIZIK_FEATURES))
    sosyal = np.zeros(len(SOSYAL_FEATURES))

    html = _preference_vector_html(fizik, sosyal, "EN")

    assert "Route / visual preferences" in html
    assert "Social / practical preferences" in html
    assert "Sea" in html
    assert "Entertainment" in html
