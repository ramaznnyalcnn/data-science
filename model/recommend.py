"""Stable recommendation facade for the Streamlit application.

The app should call this module for city shortlist generation instead of
depending on legacy model artifact details directly.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from model.config import FEATURES
from model.predict import oneri_yap, sehirleri_yukle
from model.region_ranker import filter_by_regions

RANKER_PATH = Path(__file__).parent / "artifacts" / "city_ranker.joblib"


def load_city_frame() -> pd.DataFrame:
    """Load the active destination frame with quality/dynamic layers applied."""
    return sehirleri_yukle()


def load_ranker(path: str | Path = RANKER_PATH):
    """Load the optional joblib ranker; return None for the MVP hybrid ranker."""
    path = Path(path)
    if not path.exists():
        return None
    model = joblib.load(str(path))
    expected = len(FEATURES) * 2
    trained_features = getattr(model, "n_features_in_", None)
    if trained_features is not None and int(trained_features) != expected:
        print(
            f"[Model] Joblib ranker boyutu eski ({trained_features}); "
            f"beklenen {expected}. Hybrid fallback kullanılacak."
        )
        return None
    return model


def candidate_pool_for_regions(
    base_df: pd.DataFrame,
    region_ids: list[str] | None,
    user_sosyal_v: np.ndarray | None = None,
    sort_by_social: bool = True,
) -> pd.DataFrame:
    """Apply the active scope + region shortlist filter for Stage 2."""
    region_ids = list(region_ids or [])
    pool = filter_by_regions(
        base_df,
        region_ids,
        user_sosyal_v=user_sosyal_v,
        sort_by_social=sort_by_social,
    )
    if pool.empty and region_ids:
        pool = filter_by_regions(
            base_df,
            [],
            user_sosyal_v=user_sosyal_v,
            sort_by_social=sort_by_social,
        )
    return pool.reset_index(drop=True)


def recommend_places(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    candidate_df: pd.DataFrame,
    *,
    top_n: int,
    model=None,
    aciklamalar: dict | None = None,
    u_mevsim: int | None = None,
    prefer_safety: bool = False,
    shuffle: bool = False,
) -> list[dict]:
    """Return the final hidden shortlist for the active candidate pool."""
    return oneri_yap(
        u_fiz,
        u_sos,
        candidate_df,
        gidilen_sehirler=[],
        top_n=top_n,
        model=model,
        aciklamalar=aciklamalar,
        u_mevsim=u_mevsim,
        prefer_safety=prefer_safety,
        shuffle=shuffle,
    )
