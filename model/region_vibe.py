"""Region and photo vibe scoring in sentence-embedding space."""
from __future__ import annotations

from pathlib import Path

import numpy as np

ARTIFACTS_DIR = Path(__file__).parent / "artifacts" / "embeddings"


def load_region_embeddings(artifacts_dir: Path | None = None) -> dict[str, np.ndarray]:
    """Load region_*.npy files → {region_id: (384,) float32}."""
    dir_ = Path(artifacts_dir or ARTIFACTS_DIR)
    result: dict[str, np.ndarray] = {}
    if not dir_.exists():
        return result
    for path in sorted(dir_.glob("region_*.npy")):
        result[path.stem] = np.load(str(path)).astype(np.float32)
    return result


def load_photo_embeddings(artifacts_dir: Path | None = None) -> dict[str, np.ndarray]:
    """Load photo_*.npy files → {key: (384,) float32}. key = stem without 'photo_'."""
    dir_ = Path(artifacts_dir or ARTIFACTS_DIR)
    result: dict[str, np.ndarray] = {}
    if not dir_.exists():
        return result
    for path in sorted(dir_.glob("photo_*.npy")):
        key = path.stem[len("photo_"):]
        result[key] = np.load(str(path)).astype(np.float32)
    return result


def score_regions(
    user_vibe_emb: np.ndarray,
    region_embeddings: dict[str, np.ndarray],
) -> list[tuple[str, float]]:
    """Score regions by cosine similarity to user vibe embedding.

    Returns list of (region_id, score) sorted descending.
    Assumes both user_vibe_emb and region embeddings are L2-normalized.
    """
    scores = []
    for region_id, emb in region_embeddings.items():
        sim = float(np.dot(user_vibe_emb, emb))
        scores.append((region_id, round(sim, 4)))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def update_vibe_emb(
    current: np.ndarray,
    photo_emb: np.ndarray,
    alpha: float = 0.35,
) -> np.ndarray:
    """EMA update: u ← normalize((1−α)·u + α·photo_emb)."""
    updated = (1.0 - alpha) * current + alpha * photo_emb
    norm = np.linalg.norm(updated)
    if norm > 1e-10:
        updated = updated / norm
    return updated.astype(np.float32)
