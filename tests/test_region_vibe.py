"""Tests for model/region_vibe.py — vibe scoring and EMA update."""
import numpy as np
import pytest

from model.region_vibe import score_regions, update_vibe_emb


def _unit(v: np.ndarray) -> np.ndarray:
    return (v / np.linalg.norm(v)).astype(np.float32)


@pytest.fixture
def region_embs():
    rng = np.random.default_rng(42)
    return {f"r{i:02d}": _unit(rng.standard_normal(384)) for i in range(5)}


def test_score_regions_returns_all(region_embs):
    user = _unit(np.ones(384, dtype=np.float32))
    scores = score_regions(user, region_embs)
    assert len(scores) == len(region_embs)


def test_score_regions_sorted_descending(region_embs):
    user = _unit(np.ones(384, dtype=np.float32))
    scores = score_regions(user, region_embs)
    vals = [s for _, s in scores]
    assert vals == sorted(vals, reverse=True)


def test_score_regions_perfect_match(region_embs):
    """User vibe identical to first region → that region ranks first with score ~1.0."""
    first_id = list(region_embs.keys())[0]
    user = region_embs[first_id].copy()
    scores = score_regions(user, region_embs)
    assert scores[0][0] == first_id
    assert scores[0][1] > 0.99


def test_score_regions_empty_dict():
    user = _unit(np.ones(384, dtype=np.float32))
    assert score_regions(user, {}) == []


def test_score_regions_returns_tuples(region_embs):
    user = _unit(np.ones(384, dtype=np.float32))
    scores = score_regions(user, region_embs)
    for item in scores:
        assert isinstance(item, tuple)
        assert isinstance(item[0], str)
        assert isinstance(item[1], float)


def test_update_vibe_emb_normalized():
    u = _unit(np.ones(384, dtype=np.float32))
    photo = _unit(-np.ones(384, dtype=np.float32))
    updated = update_vibe_emb(u, photo, alpha=0.35)
    assert abs(float(np.linalg.norm(updated)) - 1.0) < 1e-4


def test_update_vibe_emb_moves_toward_photo():
    u = _unit(np.array([1.0] + [0.0] * 383, dtype=np.float32))
    photo = _unit(np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32))
    updated = update_vibe_emb(u, photo, alpha=0.35)
    # updated[1] should be larger than u[1]=0.0
    assert float(updated[1]) > 0.0


def test_update_vibe_emb_alpha_zero_unchanged():
    u = _unit(np.ones(384, dtype=np.float32))
    photo = _unit(np.zeros(384, dtype=np.float32) + 0.001)
    updated = update_vibe_emb(u, photo, alpha=0.0)
    assert np.allclose(updated, u, atol=1e-4)
