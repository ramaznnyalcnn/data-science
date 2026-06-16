"""Adaptive pairwise model for verbal survey preference learning.

This model turns the survey stage into pairwise preference collection. It uses
the existing question pool, picks the next useful question, then shows the two
answer alternatives that separate the destination space most clearly.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from model.adaptive_survey import apply_answer_update, select_next_question
from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


ALL_FEATURES = FIZIK_FEATURES + SOSYAL_FEATURES


def _answer_vector(answer: dict) -> np.ndarray:
    vector = answer.get("vector", {})
    return np.array([float(vector.get(feature, 0.0)) for feature in ALL_FEATURES], dtype=float)


class AdaptivePairwiseSurveyModel:
    """Active pairwise survey model for social and trip-style preference signals."""

    name = "Adaptive Pairwise Survey Model"

    def select_question(
        self,
        u_fiz: np.ndarray,
        u_sos: np.ndarray,
        df: pd.DataFrame,
        pool: list[dict],
        asked_ids: list[str],
        skip_dims: set[str] | None = None,
    ) -> dict | None:
        return select_next_question(u_fiz, u_sos, df, pool, asked_ids, skip_dims=skip_dims)

    def select_answer_pair(
        self,
        question: dict,
        u_fiz: np.ndarray,
        u_sos: np.ndarray,
        df: pd.DataFrame | None = None,
    ) -> tuple[dict, dict] | tuple[None, None]:
        answers = question.get("answers", [])
        if len(answers) < 2:
            return (None, None)

        user = np.concatenate([u_fiz, u_sos]).astype(float)
        best_pair = None
        best_score = -1.0
        for left, right in combinations(answers, 2):
            left_v = _answer_vector(left)
            right_v = _answer_vector(right)
            separation = float(np.linalg.norm(left_v - right_v))
            midpoint = (left_v + right_v) / 2.0
            uncertainty = 1.0 - min(float(np.linalg.norm(user - midpoint)) / 3.0, 1.0)
            target_match = self._destination_contrast(left_v, right_v, df)
            score = 0.62 * separation + 0.24 * uncertainty + 0.14 * target_match
            if score > best_score:
                best_score = score
                best_pair = (left, right)
        return best_pair if best_pair is not None else (answers[0], answers[1])

    def apply_choice(
        self,
        u_fiz: np.ndarray,
        u_sos: np.ndarray,
        chosen_answer: dict,
        blend: float = 0.58,
    ) -> tuple[np.ndarray, np.ndarray]:
        return apply_answer_update(u_fiz, u_sos, chosen_answer.get("vector", {}), blend=blend)

    def _destination_contrast(
        self,
        left_v: np.ndarray,
        right_v: np.ndarray,
        df: pd.DataFrame | None,
    ) -> float:
        if df is None or df.empty:
            return 0.0
        usable = [feature for feature in ALL_FEATURES if feature in df.columns]
        if not usable:
            return 0.0
        city_v = df[usable].astype(float).values
        indices = [ALL_FEATURES.index(feature) for feature in usable]
        diff = np.abs(left_v[indices] - right_v[indices])
        if not np.any(diff):
            return 0.0
        weighted = city_v * diff
        return float(np.var(weighted, axis=0).mean())
