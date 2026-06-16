"""Question-pool based adaptive verbal survey."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


ALL_FEATURES = FIZIK_FEATURES + SOSYAL_FEATURES


def load_question_pool(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])


def _feature_value(u_fiz: np.ndarray, u_sos: np.ndarray, feature: str) -> float:
    if feature in FIZIK_FEATURES:
        return float(u_fiz[FIZIK_FEATURES.index(feature)])
    if feature in SOSYAL_FEATURES:
        return float(u_sos[SOSYAL_FEATURES.index(feature)])
    return 0.0


def _missing_need(u_fiz: np.ndarray, u_sos: np.ndarray, features: list[str]) -> float:
    if not features:
        return 0.0
    needs = []
    for feature in features:
        val = _feature_value(u_fiz, u_sos, feature)
        needs.append(1.0 if val < 0.18 else 0.65 if val < 0.45 else 0.25)
    return float(np.mean(needs))


def _answer_variance(question: dict) -> float:
    rows = []
    for answer in question.get("answers", []):
        vector = answer.get("vector", {})
        rows.append([float(vector.get(feature, 0.0)) for feature in ALL_FEATURES])
    if len(rows) < 2:
        return 0.0
    return float(np.asarray(rows, dtype=float).var(axis=0).mean())


def _destination_separation(df: pd.DataFrame, features: list[str]) -> float:
    usable = [feature for feature in features if feature in df.columns]
    if df is None or df.empty or not usable:
        return 0.0
    return float(df[usable].astype(float).var(axis=0).mean())


def select_next_question(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    pool: list[dict],
    asked_ids: list[str],
    skip_dims: set[str] | None = None,
) -> dict | None:
    """
    skip_dims: context aşamasından "biliniyor" sayılan feature'lar.
        Bu dim'leri targetlayan sorular suppress edilir; tüm targetleri biliniyorsa
        soru tamamen atlanır. Logger için atlanan soru ID'leri ayrı çağrı
        gerektirir: `questions_skipped_by_context(pool, asked_ids, skip_dims)`.
    """
    skip_dims = skip_dims or set()
    asked = set(asked_ids)
    candidates = []
    for question in pool:
        if question.get("id") in asked:
            continue
        targets = question.get("targets", [])
        # Tüm hedefler biliniyorsa atla
        if targets and all(t in skip_dims for t in targets):
            continue
        candidates.append(question)
    if not candidates:
        return None

    best = None
    best_score = -1.0
    for question in candidates:
        features = question.get("targets", [])
        # Bilinen dim'leri suppress: sadece bilinmeyenler info-gain'e katılsın
        unknown = [f for f in features if f not in skip_dims]
        coverage = len(unknown) / max(len(features), 1)
        score = (
            0.42 * _missing_need(u_fiz, u_sos, unknown)
            + 0.28 * _destination_separation(df, unknown)
            + 0.22 * _answer_variance(question)
            + 0.08 * float(question.get("priority", 0.5))
        ) * (0.4 + 0.6 * coverage)
        if score > best_score:
            best = question
            best_score = score
    return best


def questions_skipped_by_context(
    pool: list[dict], asked_ids: list[str], skip_dims: set[str] | None
) -> list[str]:
    """Tüm targetleri context-known olduğu için atlanan soruların id listesi."""
    skip_dims = skip_dims or set()
    asked = set(asked_ids)
    out = []
    for q in pool:
        qid = q.get("id")
        if qid in asked:
            continue
        targets = q.get("targets", [])
        if targets and all(t in skip_dims for t in targets):
            out.append(qid)
    return out


def apply_answer_update(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    answer_vector: dict,
    blend: float = 0.58,
) -> tuple[np.ndarray, np.ndarray]:
    new_fiz = u_fiz.astype(float).copy()
    new_sos = u_sos.astype(float).copy()
    for feature, raw_value in answer_vector.items():
        value = float(raw_value)
        if feature in FIZIK_FEATURES:
            idx = FIZIK_FEATURES.index(feature)
            new_fiz[idx] = (new_fiz[idx] * (1.0 - blend)) + (value * blend)
        elif feature in SOSYAL_FEATURES:
            idx = SOSYAL_FEATURES.index(feature)
            new_sos[idx] = (new_sos[idx] * (1.0 - blend)) + (value * blend)
    return np.clip(new_fiz, 0.0, 1.0), np.clip(new_sos, 0.0, 1.0)


def survey_should_stop(
    asked_ids: list[str],
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    min_questions: int = 3,
    max_questions: int = 5,
) -> bool:
    if len(asked_ids) >= max_questions:
        return True
    if len(asked_ids) < min_questions:
        return False
    if df is None or df.empty:
        return True

    user = np.concatenate([u_fiz, u_sos]).astype(float)
    norm = float(np.linalg.norm(user))
    if norm == 0.0:
        return False
    city_vectors = df[ALL_FEATURES].values.astype(float)
    denoms = np.linalg.norm(city_vectors, axis=1) * norm
    scores = np.divide(city_vectors @ user, denoms, out=np.zeros(len(df)), where=denoms > 0)
    if len(scores) < 2:
        return True
    top = np.sort(scores)[-2:]
    return bool((top[-1] - top[-2]) >= 0.08 and np.count_nonzero(user > 0.18) >= 6)
