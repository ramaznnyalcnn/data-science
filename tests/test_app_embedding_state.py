"""Tests for app embedding state initialization helpers."""

from __future__ import annotations

import numpy as np


def test_region_centroid_initial_user_vibe_is_normalized():
    region_embs = {
        "r1": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "r2": np.array([0.0, 1.0, 0.0], dtype=np.float32),
    }
    centroid = np.array(list(region_embs.values()), dtype=np.float32).mean(axis=0)
    centroid = centroid / np.linalg.norm(centroid)

    assert centroid.dtype == np.float32
    assert np.isclose(np.linalg.norm(centroid), 1.0)
    assert np.allclose(centroid, np.array([0.70710677, 0.70710677, 0.0], dtype=np.float32))
