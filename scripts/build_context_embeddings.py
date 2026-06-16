"""Build context and region text embeddings for NLP context matching.

Outputs:
- model/artifacts/embeddings/contexts.npz
- model/artifacts/embeddings/regions.npz

Both files use the same schema:
    ids: np.array(str)
    embeddings: np.array(float32, [N, D])
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PRESETS_PATH = ROOT / "data" / "context_presets.json"
REGIONS_PATH = ROOT / "data" / "regions.json"
OUT_DIR = ROOT / "model" / "artifacts" / "embeddings"


def _save_npz(path: Path, ids: list[str], texts: list[str]) -> None:
    from model.encoders import encode

    embs = encode(texts)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(str(path), ids=np.array(ids), embeddings=embs.astype(np.float32))
    print(f"[OK] {path} shape={embs.shape}")


def build_contexts() -> None:
    with open(PRESETS_PATH, encoding="utf-8") as f:
        presets = json.load(f)["presets"]
    ids = [preset["id"] for preset in presets]
    texts = [preset.get("text", "").strip() for preset in presets]
    _save_npz(OUT_DIR / "contexts.npz", ids, texts)


def build_regions() -> None:
    with open(REGIONS_PATH, encoding="utf-8") as f:
        regions = json.load(f)
    ids, texts = [], []
    for region in regions:
        region_id = region.get("id", "")
        parts = [region.get("hidden_description", ""), region.get("open_description", "")]
        text = " ".join(part for part in parts if part).strip()
        if region_id and text:
            ids.append(region_id)
            texts.append(text)
    _save_npz(OUT_DIR / "regions.npz", ids, texts)


def main() -> int:
    missing = [str(path) for path in (PRESETS_PATH, REGIONS_PATH) if not path.exists()]
    if missing:
        print(f"[ERROR] Missing input files: {missing}")
        return 1
    build_contexts()
    build_regions()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
