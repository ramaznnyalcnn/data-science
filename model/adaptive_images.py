"""Adaptive image-pair selector for the photo stage.

Primary path: BALD in vibe-embedding space (when user_vibe_emb + photo_embs + region_embs given).
Fallback: heuristic info-gain in feature space (original behaviour).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


def _vec(data: dict, features: list[str]) -> np.ndarray:
    return np.array([float(data.get(feature, 0.0)) for feature in features], dtype=float)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _hybrid_scores(u_fiz: np.ndarray, u_sos: np.ndarray, df: pd.DataFrame) -> np.ndarray:
    scores = []
    for _, row in df.iterrows():
        city_fiz = row[FIZIK_FEATURES].values.astype(float)
        city_sos = row[SOSYAL_FEATURES].values.astype(float)
        scores.append((_cosine(u_fiz, city_fiz) * 0.55) + (_cosine(u_sos, city_sos) * 0.45))
    return np.array(scores, dtype=float)


def _missing_weights(u_fiz: np.ndarray, u_sos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Low evidence dimensions get higher priority. Confident high dimensions still
    # keep a small value so the selector can refine rather than only fill blanks.
    fiz = np.where(u_fiz < 0.18, 1.0, np.where(u_fiz < 0.45, 0.65, 0.25))
    sos = np.where(u_sos < 0.18, 1.0, np.where(u_sos < 0.45, 0.65, 0.25))
    return fiz.astype(float), sos.astype(float)


def select_next_pair(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    pairs: list[dict],
    shown_indices: set[int],
    user_vibe_emb: np.ndarray | None = None,
    photo_embs: dict[str, np.ndarray] | None = None,
    region_embs: dict[str, np.ndarray] | None = None,
) -> int | None:
    """Pick the next image pair.

    BALD path: when user_vibe_emb, photo_embs, and region_embs are all provided,
    selects the pair with highest expected entropy reduction in embedding space.
    Fallback: heuristic info-gain in feature space (original behaviour).
    """
    if not pairs:
        return None

    if user_vibe_emb is not None and photo_embs and region_embs:
        return _select_bald(user_vibe_emb, photo_embs, region_embs, pairs, shown_indices)

    if df is None or df.empty:
        top_fiz_var = np.ones(len(FIZIK_FEATURES), dtype=float)
        top_sos_var = np.ones(len(SOSYAL_FEATURES), dtype=float)
    else:
        scores = _hybrid_scores(u_fiz, u_sos, df)
        top_n = min(8, len(df))
        top_idx = np.argsort(scores)[-top_n:]
        top_fiz_var = df.iloc[top_idx][FIZIK_FEATURES].values.astype(float).var(axis=0)
        top_sos_var = df.iloc[top_idx][SOSYAL_FEATURES].values.astype(float).var(axis=0)

    miss_fiz, miss_sos = _missing_weights(u_fiz, u_sos)
    best_idx = None
    best_score = -1.0

    for idx, pair in enumerate(pairs):
        if idx in shown_indices:
            continue

        left = pair.get("sol", {}).get("vektor", {})
        right = pair.get("sag", {}).get("vektor", {})
        left_fiz = _vec(left, FIZIK_FEATURES)
        right_fiz = _vec(right, FIZIK_FEATURES)
        left_sos = _vec(left, SOSYAL_FEATURES)
        right_sos = _vec(right, SOSYAL_FEATURES)

        diff_fiz = np.abs(left_fiz - right_fiz)
        diff_sos = np.abs(left_sos - right_sos)
        info_gain = float(np.dot(diff_fiz, top_fiz_var) + np.dot(diff_sos, top_sos_var))
        missing_gain = float(np.dot(diff_fiz, miss_fiz) + np.dot(diff_sos, miss_sos))
        relevance = max(_cosine(u_fiz, left_fiz), _cosine(u_fiz, right_fiz), 0.2)
        score = (0.5 * info_gain) + (0.4 * missing_gain) + (0.1 * relevance)

        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


def _select_bald(
    user_vibe_emb: np.ndarray,
    photo_embs: dict[str, np.ndarray],
    region_embs: dict[str, np.ndarray],
    pairs: list[dict],
    shown_indices: set[int],
) -> int | None:
    """BALD path: select pair maximising entropy reduction in region-embedding space."""
    from model.active_learning import select_next_pair as bald_select

    candidates = np.array(list(region_embs.values()), dtype=np.float32)
    if len(candidates) == 0:
        return None

    bald_pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for pair in pairs:
        sol_key = Path(pair.get("sol", {}).get("dosya", "")).stem
        sag_key = Path(pair.get("sag", {}).get("dosya", "")).stem
        e_l = photo_embs.get(sol_key)
        e_r = photo_embs.get(sag_key)
        if e_l is None or e_r is None:
            bald_pairs.append((user_vibe_emb, user_vibe_emb))
        else:
            bald_pairs.append((e_l, e_r))

    return bald_select(user_vibe_emb, candidates, bald_pairs, shown_indices)
