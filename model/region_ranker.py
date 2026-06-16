"""Region ranking and filtering helpers for the staged recommendation flow."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from model.config import FIZIK_AGIRLIK, FIZIK_FEATURES, SOSYAL_AGIRLIK, SOSYAL_FEATURES
from model.predict import weighted_cosine, W_FIZ, W_SOS


def load_regions(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _region_vector(df: pd.DataFrame, region_id: str) -> tuple[np.ndarray, np.ndarray] | None:
    rows = df[df["region_id"].eq(region_id)]
    if rows.empty:
        return None
    return (
        rows[FIZIK_FEATURES].values.astype(float).mean(axis=0),
        rows[SOSYAL_FEATURES].values.astype(float).mean(axis=0),
    )


def rank_regions(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    regions: list[dict],
    top_n: int = 3,
    user_vibe_emb: np.ndarray | None = None,
    region_embs: dict[str, np.ndarray] | None = None,
) -> list[dict]:
    """Score and return top-n regions.

    When user_vibe_emb and region_embs are provided, uses cosine similarity in
    vibe-embedding space (primary). Otherwise falls back to mean-of-cities feature
    vectors (original behaviour).
    """
    if user_vibe_emb is not None and region_embs:
        from model.region_vibe import score_regions
        vibe_scores = dict(score_regions(user_vibe_emb, region_embs))
        ranked = []
        for region in regions:
            region_id = region.get("id", "")
            score = vibe_scores.get(region_id, 0.0)
            ranked.append({**region, "score": round(float(score), 4)})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_n]

    ranked = []
    for region in regions:
        region_id = region.get("id")
        vectors = _region_vector(df, region_id)
        if vectors is None:
            continue
        r_fiz, r_sos = vectors
        score = (
            FIZIK_AGIRLIK * weighted_cosine(u_fiz, r_fiz, W_FIZ)
            + SOSYAL_AGIRLIK * weighted_cosine(u_sos, r_sos, W_SOS)
        )
        ranked.append({**region, "score": round(float(score), 4)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_n]


def filter_by_regions(
    df: pd.DataFrame,
    region_ids: list[str],
    user_sosyal_v: np.ndarray | None = None,
    sort_by_social: bool = False,
) -> pd.DataFrame:
    if not region_ids:
        out = df.copy()
    else:
        out = df[df["region_id"].isin(region_ids)].copy()

    if sort_by_social and user_sosyal_v is not None and not out.empty:
        scores = []
        for _, row in out.iterrows():
            city_sos = row[SOSYAL_FEATURES].values.astype(float)
            scores.append(weighted_cosine(user_sosyal_v, city_sos, W_SOS))
        out["_social_match"] = scores
        out = out.sort_values("_social_match", ascending=False).drop(columns=["_social_match"])

    return out.reset_index(drop=True)
