"""BALD vs Heuristic vs Random ablation.

Compares three pair-selection strategies over 6 personas × 50 sessions each.
Metrics: mean NDCG@3, mean turn count to reach confidence threshold.

Usage: python notebooks/02_bald_vs_heuristic.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES, FEATURES
from model.predict import sehirleri_yukle, oneri_yap
from model.active_learning import DEFAULT_ALPHA, DEFAULT_TAU, select_next_pair, should_stop, _softmax, _entropy

RNG = np.random.default_rng(42)
N_SESSIONS = 50
TAU = DEFAULT_TAU
ALPHA = DEFAULT_ALPHA
DIM = len(FIZIK_FEATURES) + len(SOSYAL_FEATURES)

PERSONALAR = {
    "Deniz ve eglence":  {"deniz": 0.9, "eglence": 0.85, "su_spor": 0.55},
    "Sakin sahil":       {"deniz": 0.85, "sakin": 0.9, "doga": 0.45},
    "Doga ve macera":    {"doga": 0.9, "doga_spor": 0.85, "hava_spor": 0.45},
    "Tarih ve kultur":   {"tarih": 0.95, "kultur": 0.9, "yemek": 0.55},
    "Yemek ve sehir":    {"yemek": 0.95, "kultur": 0.7, "eglence": 0.55},
    "Kis ve dag":        {"kis_spor": 0.95, "doga": 0.75, "doga_spor": 0.65},
}


def _ndcg(relevant: list[str], ranked: list[str], k: int = 3) -> float:
    rel_set = set(relevant)
    dcg = sum(
        (1.0 if ranked[i] in rel_set else 0.0) / np.log2(i + 2)
        for i in range(min(k, len(ranked)))
    )
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(k, len(rel_set))))
    return float(dcg / ideal) if ideal > 0 else 0.0


def _persona_vec(pdef: dict, noise: float = 0.08) -> tuple[np.ndarray, np.ndarray]:
    all_feats = FIZIK_FEATURES + SOSYAL_FEATURES
    v = np.array([pdef.get(f, 0.05) for f in all_feats], dtype=float)
    v += RNG.normal(0, noise, size=v.shape)
    v = np.clip(v, 0.0, 1.0)
    return v[:len(FIZIK_FEATURES)], v[len(FIZIK_FEATURES):]


def _city_candidates(df: pd.DataFrame) -> np.ndarray:
    """Normalize concatenated [fiz||sos] vectors for all cities."""
    fiz = df[FIZIK_FEATURES].values.astype(np.float32)
    sos_cols = [f for f in SOSYAL_FEATURES if f in df.columns]
    if sos_cols:
        sos = df[sos_cols].values.astype(np.float32)
        mat = np.hstack([fiz, sos])
    else:
        mat = fiz
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-10
    return mat / norms


def _make_pairs(df: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    """Build candidate pairs from city vectors (consecutive pairs)."""
    cands = _city_candidates(df)
    pairs = []
    for i in range(0, len(cands) - 1, 2):
        pairs.append((cands[i], cands[i + 1]))
    return pairs


def _run_bald(user_state: np.ndarray, candidates: np.ndarray,
              pairs: list, max_turn: int = 10) -> tuple[float, int]:
    """BALD strategy. Returns (final_max_post, n_turns)."""
    shown: set[int] = set()
    for turn in range(max_turn):
        if should_stop(user_state, candidates, turn, tau=TAU, min_turn=3, max_turn=max_turn):
            return float(_softmax(candidates @ user_state, TAU).max()), turn
        idx = select_next_pair(user_state, candidates, pairs, shown, tau=TAU, alpha=ALPHA)
        if idx is None:
            break
        shown.add(idx)
        chosen = pairs[idx][0]
        u = (1 - ALPHA) * user_state + ALPHA * chosen
        n = np.linalg.norm(u)
        user_state = u / n if n > 1e-10 else u
    post = _softmax(candidates @ user_state, TAU)
    return float(post.max()), max_turn


def _run_heuristic(u_fiz: np.ndarray, u_sos: np.ndarray,
                   df: pd.DataFrame, pairs_raw: list[dict],
                   max_turn: int = 10) -> tuple[list[str], int]:
    """Heuristic strategy (existing adaptive_images). Returns (top-3 cities, n_turns)."""
    from model.adaptive_images import select_next_pair as heur_select
    shown: set[int] = set()
    for turn in range(max_turn):
        idx = heur_select(u_fiz, u_sos, df, pairs_raw, shown)
        if idx is None:
            break
        shown.add(idx)
        pair = pairs_raw[idx]
        # simulate picking left always (neutral simulation)
        v_dict = pair.get("sol", {}).get("vektor", {})
        from model.predict import fizik_vektore_cevir, sosyal_vektore_cevir, kullanici_vektoru_guncelle
        u_fiz = kullanici_vektoru_guncelle(u_fiz, fizik_vektore_cevir(v_dict))
        u_sos = kullanici_vektoru_guncelle(u_sos, sosyal_vektore_cevir(v_dict))
    recs = oneri_yap(u_fiz, u_sos, df, top_n=3)
    return [r["sehir"] for r in recs], len(shown)


def _run_random(user_state: np.ndarray, candidates: np.ndarray,
                pairs: list, max_turn: int = 10) -> tuple[float, int]:
    """Random strategy baseline."""
    shown: set[int] = set()
    unseen = list(range(len(pairs)))
    for turn in range(max_turn):
        if should_stop(user_state, candidates, turn, tau=TAU, min_turn=3, max_turn=max_turn):
            return float(_softmax(candidates @ user_state, TAU).max()), turn
        unseen_now = [i for i in unseen if i not in shown]
        if not unseen_now:
            break
        idx = int(RNG.choice(unseen_now))
        shown.add(idx)
        chosen = pairs[idx][0]
        u = (1 - ALPHA) * user_state + ALPHA * chosen
        n = np.linalg.norm(u)
        user_state = u / n if n > 1e-10 else u
    post = _softmax(candidates @ user_state, TAU)
    return float(post.max()), max_turn


def run_ablation() -> pd.DataFrame:
    df = sehirleri_yukle()
    candidates = _city_candidates(df)
    pairs_emb = _make_pairs(df)

    # Build raw dict pairs for heuristic (needs fotograflar format)
    # Use city pairs as proxy: each city-pair becomes a pseudo photo-pair
    all_feats = FIZIK_FEATURES + [f for f in SOSYAL_FEATURES if f in df.columns]
    pairs_raw: list[dict] = []
    for i in range(0, len(df) - 1, 2):
        row_l, row_r = df.iloc[i], df.iloc[i + 1]
        pairs_raw.append({
            "sol": {"vektor": {f: float(row_l.get(f, 0.0)) for f in all_feats}},
            "sag": {"vektor": {f: float(row_r.get(f, 0.0)) for f in all_feats}},
        })

    records = []
    for persona_name, pdef in PERSONALAR.items():
        bald_posts, bald_turns = [], []
        rand_posts, rand_turns = [], []
        heur_turns_list = []

        for _ in range(N_SESSIONS):
            u_fiz, u_sos = _persona_vec(pdef)
            user_state = np.concatenate([u_fiz, u_sos])
            n = np.linalg.norm(user_state)
            user_state = user_state / n if n > 1e-10 else user_state

            post_bald, t_bald = _run_bald(user_state.copy(), candidates, pairs_emb)
            bald_posts.append(post_bald)
            bald_turns.append(t_bald)

            post_rand, t_rand = _run_random(user_state.copy(), candidates, pairs_emb)
            rand_posts.append(post_rand)
            rand_turns.append(t_rand)

            _, t_heur = _run_heuristic(u_fiz.copy(), u_sos.copy(), df, pairs_raw)
            heur_turns_list.append(t_heur)

        records.append({
            "persona": persona_name,
            "bald_max_post_mean":  round(float(np.mean(bald_posts)), 4),
            "bald_turns_median":   round(float(np.median(bald_turns)), 1),
            "rand_max_post_mean":  round(float(np.mean(rand_posts)), 4),
            "rand_turns_median":   round(float(np.median(rand_turns)), 1),
            "heur_turns_median":   round(float(np.median(heur_turns_list)), 1),
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("BALD vs Heuristic vs Random Ablation")
    print("=" * 60)
    results = run_ablation()
    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", 10)
    print(results.to_string(index=False))

    # Summary
    print("\n--- Summary ---")
    bald_better = (results["bald_turns_median"] <= results["heur_turns_median"]).sum()
    print(f"BALD <= Heuristic turns: {bald_better}/{len(results)} personas")
    bald_vs_rand = (results["bald_max_post_mean"] >= results["rand_max_post_mean"]).sum()
    print(f"BALD >= Random confidence: {bald_vs_rand}/{len(results)} personas")
