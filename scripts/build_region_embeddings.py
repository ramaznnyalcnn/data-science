#!/usr/bin/env python3
"""Build region vibe embeddings from data/regions.json.

Output: model/artifacts/embeddings/region_<id>.npy  (384-dim float32, L2-normalized)
Each region is represented by its hidden_description + open_description concatenated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
DATA_PATH = ROOT / "data" / "regions.json"
OUT_DIR = ROOT / "model" / "artifacts" / "embeddings"


def main() -> int:
    if not DATA_PATH.exists():
        print(f"[ERROR] {DATA_PATH} not found")
        return 1

    from model.encoders import encode

    with open(DATA_PATH, encoding="utf-8") as f:
        regions = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    skipped, saved = 0, 0

    for region in regions:
        region_id = region.get("id", "")
        if not region_id:
            continue

        parts = [
            region.get("hidden_description", ""),
            region.get("open_description", ""),
        ]
        text = " ".join(p for p in parts if p).strip()

        if not text:
            print(f"[SKIP] {region_id}: no description text")
            skipped += 1
            continue

        emb = encode([text])[0]
        out_path = OUT_DIR / f"{region_id}.npy"
        np.save(str(out_path), emb)
        print(f"[OK]   {region_id} → {out_path.name}")
        saved += 1

    print(f"\nDone: {saved} saved, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
