"""Unit tests for model/active_learning.py."""
import numpy as np
import pytest

from model.active_learning import _entropy, _softmax, select_next_pair, should_stop


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-10 else v


def _make_normalized(shape, seed=0):
    rng = np.random.default_rng(seed)
    if isinstance(shape, int):
        return _unit(rng.standard_normal(shape))
    return np.array([_unit(rng.standard_normal(shape[1])) for _ in range(shape[0])])


# ── _softmax and _entropy ──────────────────────────────────────────────────────

def test_softmax_sums_to_one():
    x = np.array([0.1, 0.5, -0.3, 0.8])
    p = _softmax(x, tau=0.5)
    assert abs(float(p.sum()) - 1.0) < 1e-6


def test_entropy_uniform_is_max():
    k = 10
    p_uniform = np.full(k, 1.0 / k)
    p_peaked = np.zeros(k)
    p_peaked[0] = 1.0
    assert _entropy(p_uniform) > _entropy(p_peaked)


def test_entropy_zero_for_certain():
    p = np.array([1.0, 0.0, 0.0])
    assert abs(_entropy(p)) < 1e-8


# ── select_next_pair ──────────────────────────────────────────────────────────

def test_empty_pairs_returns_none():
    user = _make_normalized(8)
    cands = _make_normalized((5, 8))
    assert select_next_pair(user, cands, [], set()) is None


def test_all_shown_returns_none():
    user = _make_normalized(8)
    cands = _make_normalized((5, 8))
    pairs = [(_make_normalized(8, i), _make_normalized(8, i + 100)) for i in range(3)]
    assert select_next_pair(user, cands, pairs, {0, 1, 2}) is None


def test_returns_valid_index():
    user = _make_normalized(8)
    cands = _make_normalized((5, 8))
    pairs = [(_make_normalized(8, i), _make_normalized(8, i + 50)) for i in range(4)]
    idx = select_next_pair(user, cands, pairs, set())
    assert 0 <= idx < 4


def test_skips_shown_indices():
    user = _make_normalized(16)
    cands = _make_normalized((10, 16))
    pairs = [(_make_normalized(16, i), _make_normalized(16, i + 100)) for i in range(5)]
    shown = {0, 2, 4}
    idx = select_next_pair(user, cands, pairs, shown)
    assert idx in {1, 3}


def test_deterministic():
    rng = np.random.default_rng(99)
    user = _unit(rng.standard_normal(16))
    cands = np.array([_unit(rng.standard_normal(16)) for _ in range(10)])
    pairs = [(_unit(rng.standard_normal(16)), _unit(rng.standard_normal(16))) for _ in range(6)]
    idx1 = select_next_pair(user, cands, pairs, set())
    idx2 = select_next_pair(user, cands, pairs, set())
    assert idx1 == idx2


def test_single_candidate_does_not_crash():
    user = _make_normalized(8)
    cands = _make_normalized((1, 8))
    pairs = [(_make_normalized(8), _make_normalized(8))]
    idx = select_next_pair(user, cands, pairs, set())
    assert idx == 0


# ── should_stop ───────────────────────────────────────────────────────────────

def test_should_stop_at_max_turn():
    user = _make_normalized(8)
    cands = _make_normalized((5, 8))
    assert should_stop(user, cands, turn=10, max_turn=10)


def test_no_stop_before_min_turn():
    user = _make_normalized(8)
    cands = _make_normalized((5, 8))
    assert not should_stop(user, cands, turn=2, min_turn=3, max_turn=10)


def test_stop_on_high_confidence():
    # user aligned with dim 0; candidates are standard basis vectors
    dim = 8
    user = np.zeros(dim)
    user[0] = 1.0
    # Each candidate is a basis vector; user is identical to cands[0]
    cands = np.eye(dim)
    # Low tau → posterior peaks at cands[0] (cosine=1.0); max(post) >> 0.5
    assert should_stop(user, cands, turn=5, tau=0.05, min_turn=3,
                       confidence_threshold=0.5)
