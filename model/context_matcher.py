"""
Context (bağlam) eşleştirici.

3 yol:
  1) NLP serbest metin   → BERT encode → preset cosine + region cosine
  2) Preset kart seçimi  → JSON'dan prior vektörler okunur, ortalama
  3) Skip                → boş partial vektör

Çıktı her zaman ortak şema:
    ContextResult(
        partial_fizik: np.ndarray[8],
        partial_sosyal: np.ndarray[5],
        known_dims: set[str],
        top_presets:  [(preset_id, score), ...],
        top_regions:  [(region_id, score), ...] | None,
        confidence:   float in [0, 1],
        method:       "nlp" | "preset" | "skip",
        nlp_text:     str | None
    )

NOT: BERT yüklenemezse veya artifacts yoksa free_text_vibe regex fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES
from model.free_text_vibe import extract_text_vibe

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRESETS_PATH = os.path.join(ROOT, "data", "context_presets.json")
CONTEXT_EMB_PATH = os.path.join(ROOT, "model", "artifacts", "embeddings", "contexts.npz")
REGION_EMB_PATH = os.path.join(ROOT, "model", "artifacts", "embeddings", "regions.npz")


@dataclass
class ContextResult:
    partial_fizik: np.ndarray
    partial_sosyal: np.ndarray
    known_dims: set
    top_presets: list = field(default_factory=list)
    top_regions: Optional[list] = None
    confidence: float = 0.0
    method: str = "skip"
    nlp_text: Optional[str] = None


# ── Preset yükleme ────────────────────────────────────────────────────────

_PRESETS_CACHE: Optional[dict] = None


def load_presets() -> dict:
    global _PRESETS_CACHE
    if _PRESETS_CACHE is None:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _PRESETS_CACHE = {p["id"]: p for p in data["presets"]}
    return _PRESETS_CACHE


def preset_to_vectors(preset: dict) -> tuple[np.ndarray, np.ndarray]:
    fiz = np.full(len(FIZIK_FEATURES), np.nan, dtype=float)
    sos = np.full(len(SOSYAL_FEATURES), np.nan, dtype=float)
    for k, v in preset.get("fizik", {}).items():
        if k in FIZIK_FEATURES:
            fiz[FIZIK_FEATURES.index(k)] = float(v)
    for k, v in preset.get("sosyal", {}).items():
        if k in SOSYAL_FEATURES:
            sos[SOSYAL_FEATURES.index(k)] = float(v)
    return fiz, sos


def average_partials(vec_list: list[np.ndarray]) -> np.ndarray:
    """NaN-aware ortalama: bir dim sadece dolu olanlardan ortalama alır."""
    if not vec_list:
        return np.full_like(vec_list[0] if vec_list else np.zeros(1), np.nan)
    stacked = np.stack(vec_list, axis=0)
    with np.errstate(all="ignore"):
        out = np.nanmean(stacked, axis=0)
    return out


def known_dims_from_partials(
    fiz: np.ndarray, sos: np.ndarray, confidence: float, threshold: float = 0.25
) -> set:
    """
    Bir dim 'biliniyor' sayılır eğer:
        |value - 0.5| > threshold  AND  confidence > 0.5
    NaN olan dimler 'bilinmiyor'.
    """
    known = set()
    if confidence <= 0.5:
        return known
    for i, name in enumerate(FIZIK_FEATURES):
        v = fiz[i]
        if not np.isnan(v) and abs(v - 0.5) > threshold:
            known.add(name)
    for i, name in enumerate(SOSYAL_FEATURES):
        v = sos[i]
        if not np.isnan(v) and abs(v - 0.5) > threshold:
            known.add(name)
    return known


# ── Embedding yükleme ─────────────────────────────────────────────────────

_CTX_EMB_CACHE: Optional[dict] = None
_REG_EMB_CACHE: Optional[dict] = None


def _load_npz(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    npz = np.load(path, allow_pickle=False)
    return {"ids": list(npz["ids"]), "embeddings": npz["embeddings"]}


def load_context_embeddings() -> Optional[dict]:
    global _CTX_EMB_CACHE
    if _CTX_EMB_CACHE is None:
        _CTX_EMB_CACHE = _load_npz(CONTEXT_EMB_PATH)
    return _CTX_EMB_CACHE


def load_region_embeddings() -> Optional[dict]:
    global _REG_EMB_CACHE
    if _REG_EMB_CACHE is None:
        _REG_EMB_CACHE = _load_npz(REGION_EMB_PATH)
    return _REG_EMB_CACHE


# ── Text encoder (lazy) ───────────────────────────────────────────────────

_ENCODER = None


def get_encoder():
    """Lazy load shared text encoder. Failure → None (regex fallback)."""
    global _ENCODER
    if _ENCODER is False:
        return None
    if _ENCODER is None:
        try:
            from model.encoders import encode

            class _Encoder:
                def _encode(self, text: str) -> np.ndarray:
                    return encode([text])[0]

            _ENCODER = _Encoder()
        except Exception as e:
            print(f"[CTX] Text encoder yüklenemedi: {e}; regex fallback aktif.")
            _ENCODER = False
            return None
    return _ENCODER


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── Public API ────────────────────────────────────────────────────────────

def from_skip() -> ContextResult:
    return ContextResult(
        partial_fizik=np.full(len(FIZIK_FEATURES), np.nan),
        partial_sosyal=np.full(len(SOSYAL_FEATURES), np.nan),
        known_dims=set(),
        confidence=0.0,
        method="skip",
    )


def from_presets(picked_ids: list[str]) -> ContextResult:
    presets = load_presets()
    valid = [presets[i] for i in picked_ids if i in presets]
    if not valid:
        return from_skip()

    fiz_vecs, sos_vecs = [], []
    implied = set()
    for p in valid:
        fz, ss = preset_to_vectors(p)
        fiz_vecs.append(fz)
        sos_vecs.append(ss)
        implied.update(p.get("implies_dims", []))

    fiz = average_partials(fiz_vecs)
    sos = average_partials(sos_vecs)

    confidence = 0.7 if len(valid) == 1 else 0.85

    return ContextResult(
        partial_fizik=fiz,
        partial_sosyal=sos,
        known_dims=implied,
        top_presets=[(p["id"], 1.0) for p in valid],
        confidence=confidence,
        method="preset",
    )


def from_nlp(text: str, top_k: int = 2) -> ContextResult:
    """
    Serbest metni encode et, en yakın preset'leri bul, vektör ortalaması üret.
    Encoder yoksa regex fallback'e düş.
    """
    text = (text or "").strip()
    if not text:
        return from_skip()

    encoder = get_encoder()
    ctx_emb = load_context_embeddings()

    if encoder is None or ctx_emb is None:
        # Regex fallback
        fz, ss, conf = extract_text_vibe(text)
        # extract_text_vibe 0 yerine 0 dolduruyor; NaN'a çevir bilinmeyenler için
        fiz = np.where(fz > 0, fz, np.nan)
        sos = np.where(ss > 0, ss, np.nan)
        return ContextResult(
            partial_fizik=fiz,
            partial_sosyal=sos,
            known_dims=known_dims_from_partials(fiz, sos, conf),
            confidence=conf,
            method="nlp",
            nlp_text=text,
        )

    user_emb = encoder._encode(text)

    # Preset cosine
    sims = np.array([_cosine(user_emb, e) for e in ctx_emb["embeddings"]])
    order = np.argsort(-sims)
    top = [(ctx_emb["ids"][i], float(sims[i])) for i in order[: top_k]]

    # Top-2 ağırlıklı ortalama
    presets = load_presets()
    fiz_vecs, sos_vecs, weights = [], [], []
    implied = set()
    for pid, sim in top:
        if pid not in presets:
            continue
        fz, ss = preset_to_vectors(presets[pid])
        fiz_vecs.append(fz)
        sos_vecs.append(ss)
        weights.append(max(sim, 0.0))
        implied.update(presets[pid].get("implies_dims", []))

    if not fiz_vecs:
        return from_skip()

    w = np.array(weights, dtype=float)
    if w.sum() == 0:
        w = np.ones_like(w)
    w = w / w.sum()

    fiz_stack = np.stack(fiz_vecs, axis=0)
    sos_stack = np.stack(sos_vecs, axis=0)
    fiz = _weighted_nanmean(fiz_stack, w)
    sos = _weighted_nanmean(sos_stack, w)

    # Confidence = top1 ile top2 cosine kontrastı (kaç sınıfa benziyor)
    contrast = float(top[0][1] - top[1][1]) if len(top) >= 2 else float(top[0][1])
    confidence = float(np.clip(0.5 + contrast * 5.0, 0.0, 1.0))

    # Region cosine (varsa)
    top_regions = None
    reg_emb = load_region_embeddings()
    if reg_emb is not None:
        rsims = np.array([_cosine(user_emb, e) for e in reg_emb["embeddings"]])
        rorder = np.argsort(-rsims)
        top_regions = [(reg_emb["ids"][i], float(rsims[i])) for i in rorder[:3]]

    return ContextResult(
        partial_fizik=fiz,
        partial_sosyal=sos,
        known_dims=implied | known_dims_from_partials(fiz, sos, confidence),
        top_presets=top,
        top_regions=top_regions,
        confidence=confidence,
        method="nlp",
        nlp_text=text,
    )


def _weighted_nanmean(stack: np.ndarray, w: np.ndarray) -> np.ndarray:
    """NaN-aware weighted mean along axis=0."""
    out = np.full(stack.shape[1], np.nan)
    for j in range(stack.shape[1]):
        col = stack[:, j]
        mask = ~np.isnan(col)
        if not mask.any():
            continue
        ww = w[mask]
        if ww.sum() == 0:
            out[j] = float(col[mask].mean())
        else:
            out[j] = float((col[mask] * ww).sum() / ww.sum())
    return out


def blend_into_user(
    u_fiz: np.ndarray, u_sos: np.ndarray, ctx: ContextResult, blend: float = 0.35
) -> tuple[np.ndarray, np.ndarray]:
    """
    Mevcut kullanıcı vektörüne context partial'ını karıştır.
    Sadece NaN olmayan dimleri günceller.
    """
    new_fiz = u_fiz.astype(float).copy()
    new_sos = u_sos.astype(float).copy()
    if ctx.confidence <= 0:
        return new_fiz, new_sos

    eff = blend * (0.5 + 0.5 * ctx.confidence)

    for i in range(len(FIZIK_FEATURES)):
        v = ctx.partial_fizik[i]
        if not np.isnan(v):
            new_fiz[i] = (1 - eff) * new_fiz[i] + eff * v
    for i in range(len(SOSYAL_FEATURES)):
        v = ctx.partial_sosyal[i]
        if not np.isnan(v):
            new_sos[i] = (1 - eff) * new_sos[i] + eff * v

    return np.clip(new_fiz, 0.0, 1.0), np.clip(new_sos, 0.0, 1.0)
