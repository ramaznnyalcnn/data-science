"""Lightweight free-text vibe extraction for destination features."""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


CHAR_MAP = str.maketrans({
    "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O", "ş": "s", "Ş": "S", "ü": "u", "Ü": "U",
})

KEYWORDS = {
    "deniz": ["deniz", "plaj", "sahil", "koy", "ada", "yuzme", "mavi", "kiyi"],
    "doga": ["doga", "orman", "dag", "yayla", "gol", "vadi", "manzara", "yesil"],
    "tarih": ["tarih", "antik", "arkeoloji", "kale", "muze", "harabe", "kalinti"],
    "kultur": ["kultur", "yerel", "otantik", "gelenek", "sanat", "mimari", "festival"],
    "doga_spor": ["yuruyus", "trekking", "hiking", "kamp", "rota", "macera"],
    "su_spor": ["su sporu", "dalis", "sorf", "surf", "tekne", "rafting", "jet ski"],
    "hava_spor": ["parasut", "parasutu", "balon", "ucus", "adrenalin"],
    "kis_spor": ["kis", "kar", "kayak", "snowboard", "ski"],
    "eglence": ["eglence", "gece", "bar", "kulup", "canli", "sosyal", "kalabalik"],
    "sakin": ["sakin", "sessiz", "huzurlu", "dinlenme", "tenha", "rahat"],
    "yemek": ["yemek", "lezzet", "gastronomi", "mutfak", "restoran", "pazar"],
    "ulasim_kolayligi": ["kolay ulasim", "merkezi", "yuruyerek", "toplu tasima", "pratik"],
    "fiyat": ["luks", "konfor", "premium", "resort", "butik", "kaliteli"],
}

NEGATIVE_PATTERNS = {
    "eglence": ["kalabalik olmasin", "gece hayati olmasin", "gurultu olmasin"],
    "fiyat": ["pahali olmasin", "butce", "uygun fiyat", "ucuz", "orta butce"],
}


def normalize_text(text: str) -> str:
    text = text.translate(CHAR_MAP)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def extract_text_vibe(text: str) -> tuple[np.ndarray, np.ndarray, float]:
    clean = normalize_text(text or "")
    fiz = np.zeros(len(FIZIK_FEATURES), dtype=float)
    sos = np.zeros(len(SOSYAL_FEATURES), dtype=float)
    if not clean:
        return fiz, sos, 0.0

    hits = 0
    for feature, terms in KEYWORDS.items():
        count = sum(1 for term in terms if normalize_text(term) in clean)
        if count <= 0:
            continue
        value = min(0.35 + count * 0.18, 0.95)
        if feature in FIZIK_FEATURES:
            fiz[FIZIK_FEATURES.index(feature)] = value
        elif feature in SOSYAL_FEATURES:
            sos[SOSYAL_FEATURES.index(feature)] = value
        hits += count

    for feature, patterns in NEGATIVE_PATTERNS.items():
        if any(normalize_text(pattern) in clean for pattern in patterns):
            if feature == "eglence":
                sos[SOSYAL_FEATURES.index("eglence")] = min(sos[SOSYAL_FEATURES.index("eglence")], 0.15)
                sos[SOSYAL_FEATURES.index("sakin")] = max(sos[SOSYAL_FEATURES.index("sakin")], 0.82)
            elif feature == "fiyat":
                sos[SOSYAL_FEATURES.index("fiyat")] = 0.25
            hits += 1

    confidence = min(hits / 6.0, 1.0)
    return fiz, sos, round(float(confidence), 3)


def blend_text_vibe(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    text_fiz: np.ndarray,
    text_sos: np.ndarray,
    confidence: float,
) -> tuple[np.ndarray, np.ndarray]:
    if confidence <= 0:
        return u_fiz, u_sos
    blend = min(0.18 + confidence * 0.22, 0.40)
    mask_fiz = text_fiz > 0
    mask_sos = text_sos > 0
    new_fiz = u_fiz.astype(float).copy()
    new_sos = u_sos.astype(float).copy()
    new_fiz[mask_fiz] = new_fiz[mask_fiz] * (1.0 - blend) + text_fiz[mask_fiz] * blend
    new_sos[mask_sos] = new_sos[mask_sos] * (1.0 - blend) + text_sos[mask_sos] * blend
    return np.clip(new_fiz, 0.0, 1.0), np.clip(new_sos, 0.0, 1.0)
