"""Tests for Stage 1 adaptive image pair selection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from model.adaptive_images import select_next_pair


def _unit(values):
    arr = np.array(values, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def test_embedding_args_take_bald_path(monkeypatch):
    import model.active_learning as active_learning

    called = {}

    def fake_bald(user_state, candidates, pairs, shown_indices):
        called["user_state"] = user_state
        called["candidates"] = candidates
        called["pairs"] = pairs
        called["shown_indices"] = shown_indices
        return 1

    monkeypatch.setattr(active_learning, "select_next_pair", fake_bald)

    pairs = [
        {"sol": {"dosya": "a.jpg", "vektor": {}}, "sag": {"dosya": "b.jpg", "vektor": {}}},
        {"sol": {"dosya": "c.jpg", "vektor": {}}, "sag": {"dosya": "d.jpg", "vektor": {}}},
    ]
    idx = select_next_pair(
        np.zeros(8),
        np.zeros(5),
        pd.DataFrame(),
        pairs,
        shown_indices=set(),
        user_vibe_emb=_unit([1.0, 0.0, 0.0]),
        photo_embs={
            "a": _unit([1.0, 0.0, 0.0]),
            "b": _unit([0.0, 1.0, 0.0]),
            "c": _unit([0.0, 0.0, 1.0]),
            "d": _unit([1.0, 1.0, 0.0]),
        },
        region_embs={
            "r1": _unit([1.0, 0.0, 0.0]),
            "r2": _unit([0.0, 1.0, 0.0]),
        },
    )

    assert idx == 1
    assert called["candidates"].shape == (2, 3)
    assert len(called["pairs"]) == 2


def test_missing_embedding_args_use_heuristic_fallback():
    pairs = [
        {
            "sol": {"vektor": {"deniz": 1.0, "eglence": 1.0}},
            "sag": {"vektor": {"doga": 1.0, "sakin": 1.0}},
        }
    ]
    idx = select_next_pair(np.zeros(8), np.zeros(5), pd.DataFrame(), pairs, shown_indices=set())
    assert idx == 0
