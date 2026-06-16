"""Adaptive pairwise model for photo-driven region preference prediction.

This is a non-parametric model layer: it does not learn fitted coefficients from
offline training yet, but it maintains the project-level model boundary for the
adaptive pairwise stage. The downstream city shortlist uses the active hybrid
ranker facade unless a compatible joblib artifact is present.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from model.adaptive_images import select_next_pair
from model.region_ranker import rank_regions


class AdaptivePairwiseRegionModel:
    """Photo-pair active learning model that predicts likely travel regions."""

    name = "Adaptive Pairwise Region Model"

    def select_photo_pair(
        self,
        u_fiz: np.ndarray,
        u_sos: np.ndarray,
        df: pd.DataFrame,
        pairs: list[dict],
        shown_indices: set[int],
    ) -> int | None:
        return select_next_pair(u_fiz, u_sos, df, pairs, shown_indices)

    def predict_regions(
        self,
        u_fiz: np.ndarray,
        u_sos: np.ndarray,
        df: pd.DataFrame,
        regions: list[dict],
        top_n: int = 3,
    ) -> list[dict]:
        return rank_regions(u_fiz, u_sos, df, regions, top_n=top_n)
