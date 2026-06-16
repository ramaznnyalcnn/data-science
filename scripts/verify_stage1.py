"""Quick project health checks for the travel recommender demo."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES  # noqa: E402
from model.predict import oneri_yap, sehirleri_yukle  # noqa: E402
from model.scope_filter import (  # noqa: E402
    SCOPE_ABROAD,
    SCOPE_TURKEY,
    VISA_FREE,
    VISA_INCLUDE_REQUIRED,
    filter_destinations,
)


def _failures() -> list[str]:
    failures: list[str] = []

    df = sehirleri_yukle()
    required = ["sehir", "region_id", "country", "visa_free", "mevsim"] + FIZIK_FEATURES + SOSYAL_FEATURES
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        failures.append(f"Missing columns: {missing_cols}")

    for col in FIZIK_FEATURES + SOSYAL_FEATURES:
        values = pd.to_numeric(df[col], errors="coerce")
        if values.isna().any() or (values.lt(0) | values.gt(1)).any():
            failures.append(f"Invalid numeric range in {col}")

    regions_path = ROOT / "data" / "regions.json"
    regions = json.loads(regions_path.read_text(encoding="utf-8"))
    region_ids = {r["id"] for r in regions}
    missing_regions = sorted(set(df["region_id"]) - region_ids)
    if missing_regions:
        failures.append(f"CSV region_id not found in regions.json: {missing_regions[:10]}")

    photo_path = ROOT / "data" / "fotograflar.json"
    photos = json.loads(photo_path.read_text(encoding="utf-8"))
    missing_photos = []
    for group in ("kategoriler", "turlar"):
        for i, item in enumerate(photos.get(group, [])):
            for side in ("sol", "sag"):
                name = item.get(side, {}).get("dosya")
                if name and not (ROOT / "photos" / name).exists():
                    missing_photos.append(f"{group}[{i}].{side}: {name}")
    if missing_photos:
        failures.append(f"Missing local photos: {missing_photos[:10]}")

    u_fiz = np.full(len(FIZIK_FEATURES), 0.5)
    u_sos = np.full(len(SOSYAL_FEATURES), 0.5)
    for label, scope, visa in (
        ("turkey", SCOPE_TURKEY, VISA_FREE),
        ("abroad", SCOPE_ABROAD, VISA_INCLUDE_REQUIRED),
    ):
        active = filter_destinations(df, scope, visa)
        if active.empty:
            failures.append(f"{label} filter produced empty destination set")
            continue
        try:
            recs = oneri_yap(u_fiz, u_sos, active, top_n=3)
        except Exception as exc:  # pragma: no cover - diagnostic script
            failures.append(f"{label} recommendation crashed: {exc}")
            continue
        if not recs:
            failures.append(f"{label} recommendation returned no results")

    return failures


def main() -> int:
    failures = _failures()
    if failures:
        print("[verify] FAILED")
        for item in failures:
            print(f"- {item}")
        return 1
    print("[verify] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
