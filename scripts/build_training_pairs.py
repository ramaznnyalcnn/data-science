#!/usr/bin/env python3
"""Convert data/sessions.jsonl → data/training_pairs.parquet.

Each session's stage2_user_pick beats each other shown city → pairwise rows.
Feature vector: [u_fiz || u_sos || picked_city || other_city] (39-dim),
label=1 (picked>other). Each city vector is the 13-dim 8+5 plan vector.
City features looked up from model_destinasyonlar.csv.
"""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SESSIONS_PATH = DATA_DIR / "sessions.jsonl"
CITIES_CSV = DATA_DIR / "model_destinasyonlar.csv"
OUT_PATH = DATA_DIR / "training_pairs.parquet"

FIZIK_FEATURES = ["deniz", "doga", "tarih", "kultur", "doga_spor", "su_spor", "hava_spor", "kis_spor"]
SOSYAL_FEATURES = ["eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat"]


def _load_cities() -> dict[str, np.ndarray]:
    if not CITIES_CSV.exists():
        return {}
    df = pd.read_csv(CITIES_CSV)
    city_vecs: dict[str, np.ndarray] = {}
    all_feats = FIZIK_FEATURES + SOSYAL_FEATURES
    available = [f for f in all_feats if f in df.columns]
    for _, row in df.iterrows():
        name = str(row.get("sehir", "")).strip()
        if not name:
            continue
        vec = np.array([float(row.get(f, 0.0)) for f in available], dtype=np.float32)
        city_vecs[name] = vec
    return city_vecs


def main() -> None:
    if not SESSIONS_PATH.exists():
        print(f"[SKIP] {SESSIONS_PATH} not found")
        return

    city_vecs = _load_cities()
    if not city_vecs:
        print(f"[WARN] No city vectors loaded from {CITIES_CSV}")

    records = []
    with open(SESSIONS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                session = json.loads(line)
            except json.JSONDecodeError:
                continue

            session_id = session.get("session_id", "")
            stage2 = session.get("stage2_recommendations", {})
            if not stage2:
                continue

            pick = stage2.get("user_pick") or stage2.get("click_city")
            display = stage2.get("shown_order") or stage2.get("display_order", [])
            u_fiz_raw = session.get("u_fiz") or stage2.get("u_fiz")
            u_sos_raw = session.get("u_sos") or stage2.get("u_sos")

            if not (pick and display and u_fiz_raw and u_sos_raw):
                continue

            u_fiz = np.array(u_fiz_raw, dtype=np.float32)
            u_sos = np.array(u_sos_raw, dtype=np.float32)
            pick_vec = city_vecs.get(pick)

            for other in display:
                if other == pick:
                    continue
                other_vec = city_vecs.get(other)
                if pick_vec is None or other_vec is None:
                    continue

                feat = np.concatenate([u_fiz, u_sos, pick_vec, other_vec])
                records.append({
                    "session_id": session_id,
                    "pick": pick,
                    "other": other,
                    "features": feat.tolist(),
                    "label": 1,
                })

    if not records:
        print(f"[WARN] No training pairs extracted. Check sessions.jsonl schema.")
        return

    df = pd.DataFrame(records)
    df.to_parquet(OUT_PATH, index=False)
    print(f"[OK] {len(df)} pairs from {df['session_id'].nunique()} sessions → {OUT_PATH}")


if __name__ == "__main__":
    main()
