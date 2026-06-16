"""Destination pool filtering for Turkey / abroad and visa-free flow."""

from __future__ import annotations

import pandas as pd


TURKEY_NAME = "Turkiye"
SCOPE_TURKEY = "turkiye"
SCOPE_ABROAD = "yurtdisi"
SCOPE_MIXED = "karisik"
VISA_FREE = "vizesiz"
VISA_INCLUDE_REQUIRED = "vizeli_dahil"


def _visa_free_mask(df: pd.DataFrame) -> pd.Series:
    if "visa_free" not in df.columns:
        return pd.Series(True, index=df.index)
    values = df["visa_free"]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes", "y", "vizesiz", "free"}
    )


def filter_destinations(
    df: pd.DataFrame,
    scope_mode: str = SCOPE_MIXED,
    visa_mode: str = VISA_FREE,
) -> pd.DataFrame:
    """Return the active recommendation pool for the selected travel scope."""
    if df is None or df.empty:
        return df.copy()

    out = df.copy()
    is_turkey = out["country"].eq(TURKEY_NAME) if "country" in out.columns else pd.Series(True, index=out.index)

    if scope_mode == SCOPE_TURKEY:
        out = out[is_turkey]
    elif scope_mode == SCOPE_ABROAD:
        out = out[~is_turkey]
    elif scope_mode != SCOPE_MIXED:
        raise ValueError(f"Unknown scope_mode: {scope_mode}")

    if visa_mode == VISA_FREE:
        is_turkey = out["country"].eq(TURKEY_NAME) if "country" in out.columns else pd.Series(True, index=out.index)
        out = out[is_turkey | _visa_free_mask(out)]
    elif visa_mode != VISA_INCLUDE_REQUIRED:
        raise ValueError(f"Unknown visa_mode: {visa_mode}")

    return out.reset_index(drop=True)


def needs_visa_filter(df: pd.DataFrame, scope_mode: str) -> bool:
    if scope_mode == SCOPE_TURKEY or df is None or df.empty or "country" not in df.columns:
        return False
    if scope_mode == SCOPE_ABROAD:
        return True
    return bool((~df["country"].eq(TURKEY_NAME)).any())
