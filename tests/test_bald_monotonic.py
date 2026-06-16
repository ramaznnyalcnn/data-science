"""BALD monotonicity: max(posterior) should generally increase over turns."""
import numpy as np
import pytest

from model.active_learning import _entropy, _softmax, select_next_pair


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-10 else v


def _simulate(n_cand=15, n_pairs=8, dim=32, tau=0.18, alpha=0.35, seed=7):
    """Run 4 BALD turns and track posterior statistics."""
    rng = np.random.default_rng(seed)
    candidates = np.array([_unit(rng.standard_normal(dim)) for _ in range(n_cand)])
    pairs_raw = [
        (_unit(rng.standard_normal(dim)), _unit(rng.standard_normal(dim)))
        for _ in range(n_pairs)
    ]
    user = _unit(rng.standard_normal(dim))

    max_posts = []
    entropies = []
    shown: set[int] = set()

    for _ in range(4):
        post = _softmax(candidates @ user, tau)
        max_posts.append(float(post.max()))
        entropies.append(_entropy(post))

        idx = select_next_pair(user, candidates, pairs_raw, shown, tau=tau, alpha=alpha)
        if idx is None:
            break
        shown.add(idx)
        chosen_emb = pairs_raw[idx][0]
        new_u = (1 - alpha) * user + alpha * chosen_emb
        norm = np.linalg.norm(new_u)
        user = new_u / norm if norm > 1e-10 else new_u

    return max_posts, entropies


def test_max_posterior_nondecreasing_trend():
    """Overall max(posterior) should not fall dramatically over turns."""
    max_posts, _ = _simulate(seed=7)
    assert len(max_posts) >= 3
    # Allow small fluctuation; final should be >= initial * 0.9
    assert max_posts[-1] >= max_posts[0] * 0.90


def test_entropy_trend_decreasing():
    """Entropy should not grow dramatically — trend should be down."""
    _, entropies = _simulate(seed=7)
    assert len(entropies) >= 3
    # Final entropy should be at most 10% higher than initial (allow noise)
    assert entropies[-1] <= entropies[0] * 1.10


def test_multiple_seeds_stable():
    """Run over several seeds; majority should show non-increasing entropy."""
    wins = 0
    for seed in range(10):
        _, entropies = _simulate(seed=seed)
        if entropies[-1] <= entropies[0]:
            wins += 1
    assert wins >= 6, f"Only {wins}/10 seeds showed non-increasing entropy"


def test_bald_picks_high_gain_pair():
    """The selected pair should have non-negative gain over random selection."""
    rng = np.random.default_rng(42)
    dim = 16
    n_cand = 10
    candidates = np.array([_unit(rng.standard_normal(dim)) for _ in range(n_cand)])
    user = _unit(rng.standard_normal(dim))
    tau = 0.18
    alpha = 0.35

    pairs = [(_unit(rng.standard_normal(dim)), _unit(rng.standard_normal(dim))) for _ in range(6)]

    from model.active_learning import _softmax, _entropy
    post = _softmax(candidates @ user, tau)
    h_now = _entropy(post)

    best_idx = select_next_pair(user, candidates, pairs, set(), tau=tau, alpha=alpha)
    assert best_idx is not None

    e_l, e_r = pairs[best_idx]
    u_l = _unit((1 - alpha) * user + alpha * e_l)
    u_r = _unit((1 - alpha) * user + alpha * e_r)
    gain = h_now - 0.5 * (_entropy(_softmax(candidates @ u_l, tau)) +
                           _entropy(_softmax(candidates @ u_r, tau)))
    assert gain >= 0.0
