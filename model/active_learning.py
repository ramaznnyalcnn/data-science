"""BALD-style adaptive pairwise selector.

Shared by Stage 1 (photo/region space) and Stage 1.7 (survey/feature space).
All inputs must be L2-normalized vectors.
"""
from __future__ import annotations

import numpy as np

DEFAULT_TAU = 0.10
DEFAULT_ALPHA = 0.45


def _softmax(sims: np.ndarray, tau: float) -> np.ndarray:
    z = sims / tau
    z = z - z.max()
    exp_z = np.exp(z)
    return exp_z / (exp_z.sum() + 1e-12)


def _entropy(p: np.ndarray) -> float:
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))


def select_next_pair(
    user_state: np.ndarray,
    candidates: np.ndarray,
    pairs: list[tuple[np.ndarray, np.ndarray]],
    shown_idx: set[int],
    tau: float = DEFAULT_TAU,
    alpha: float = DEFAULT_ALPHA,
) -> int | None:
    """Pick the unseen pair with highest expected entropy reduction (BALD).

    Args:
        user_state: (D,) normalized embedding — current user belief.
        candidates:  (K, D) normalized embeddings — items being ranked.
        pairs:       list of (left_emb, right_emb) — each emb is (D,) normalized.
        shown_idx:   indices already shown; these are skipped.
        tau:         softmax temperature (lower → more peaked posterior).
        alpha:       EMA step size for simulated user-state update.

    Returns:
        Index into `pairs` of the best next pair, or None if all shown.
    """
    if not pairs:
        return None

    sims = candidates @ user_state
    post = _softmax(sims, tau)
    h_now = _entropy(post)

    best_gain = -float("inf")
    best_i: int | None = None

    for i, (e_l, e_r) in enumerate(pairs):
        if i in shown_idx:
            continue

        u_l = (1.0 - alpha) * user_state + alpha * e_l
        n_l = np.linalg.norm(u_l)
        u_l = u_l / n_l if n_l > 1e-10 else u_l

        u_r = (1.0 - alpha) * user_state + alpha * e_r
        n_r = np.linalg.norm(u_r)
        u_r = u_r / n_r if n_r > 1e-10 else u_r

        h_l = _entropy(_softmax(candidates @ u_l, tau))
        h_r = _entropy(_softmax(candidates @ u_r, tau))
        gain = h_now - 0.5 * (h_l + h_r)

        if gain > best_gain:
            best_gain = gain
            best_i = i

    return best_i


def should_stop(
    user_state: np.ndarray,
    candidates: np.ndarray,
    turn: int,
    tau: float = DEFAULT_TAU,
    min_turn: int = 3,
    max_turn: int = 10,
    confidence_threshold: float = 0.55,
    entropy_ratio: float = 0.6,
) -> bool:
    """Return True when posterior is confident enough to stop asking.

    Stops when ANY of:
      - turn >= max_turn
      - turn >= min_turn AND max(posterior) > confidence_threshold
      - turn >= min_turn AND H(posterior) < entropy_ratio * H(uniform)
    """
    if turn >= max_turn:
        return True
    if turn < min_turn:
        return False
    K = max(len(candidates), 2)
    post = _softmax(candidates @ user_state, tau)
    if float(post.max()) > confidence_threshold:
        return True
    return _entropy(post) < entropy_ratio * np.log(K)
