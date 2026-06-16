"""Sentence-transformer encoder — lazy load, L2-normalized output."""
from __future__ import annotations

import hashlib

import numpy as np

_model = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_NAME = _MODEL_NAME
EMB_DIM = 384


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            _model = False
        else:
            _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _fallback_encode(texts: list[str]) -> np.ndarray:
    rows = []
    for text in texts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little", signed=False)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(EMB_DIM).astype(np.float32)
        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec /= norm
        rows.append(vec)
    return np.array(rows, dtype=np.float32)


def encode(texts: list[str]) -> np.ndarray:
    """Encode texts → (N, 384) float32, L2-normalized rows."""
    if not texts:
        return np.zeros((0, EMB_DIM), dtype=np.float32)
    model = _get_model()
    if model is False:
        return _fallback_encode(texts)
    embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(embs, dtype=np.float32)
