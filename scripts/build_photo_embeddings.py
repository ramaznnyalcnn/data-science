#!/usr/bin/env python3
"""Build photo proxy embeddings from data/fotograflar.json.

Output: model/artifacts/embeddings/photo_<stem>.npy  (384-dim float32, L2-normalized)
Each photo is represented by its Turkish aciklama (description) text.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
DATA_PATH = ROOT / "data" / "fotograflar.json"
OUT_DIR = ROOT / "model" / "artifacts" / "embeddings"


def main() -> int:
    if not DATA_PATH.exists():
        print(f"[ERROR] {DATA_PATH} not found")
        return 1

    from model.encoders import encode

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    skipped, saved = 0, 0

    items = list(data.get("kategoriler", [])) + list(data.get("turlar", []))
    for kat in items:
        for side in ("sol", "sag"):
            foto = kat.get(side, {})
            dosya = foto.get("dosya", "")
            aciklama = foto.get("aciklama", "").strip()

            if not aciklama:
                print(f"[SKIP] {dosya}: no aciklama")
                skipped += 1
                continue

            key = Path(dosya).stem
            emb = encode([aciklama])[0]
            out_path = OUT_DIR / f"photo_{key}.npy"
            np.save(str(out_path), emb)
            print(f"[OK]   {key} → {out_path.name}")
            saved += 1

    print(f"\nDone: {saved} saved, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
