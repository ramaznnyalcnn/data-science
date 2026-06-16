"""
Tahmin motoru: çift vektör cosine + mevsim penalty + adaptif soru seçimi.

Kullanıcı ve şehirler iki ayrı vektörle temsil edilir:
  fiziksel  (8 boyut): deniz, doga, tarih, kultur, doga_spor, su_spor, hava_spor, kis_spor
  sosyolojik (5 boyut): eglence, sakin, yemek, ulasim_kolayligi, fiyat
"""

import os
import json
import random

import numpy as np
import pandas as pd

from model.config import (
    FIZIK_FEATURES, SOSYAL_FEATURES, FEATURES,
    FIZIK_WEIGHTS, SOSYAL_WEIGHTS,
    FIZIK_AGIRLIK, SOSYAL_AGIRLIK, MEVSIM_CARPAN,
    QUALITY_FEATURES, QUALITY_WEIGHTS,
    TIPLER, MIN_FOTO, MAX_FOTO, GUVEN_ESIGI,
)
from model.adaptive_images import select_next_pair

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_DATA_PATH = os.path.join(DATA_DIR, "model_destinasyonlar.csv")
SAFETY_DATA_PATH = os.path.join(DATA_DIR, "city_safety.json")
DYNAMIC_ADJUSTMENTS_PATH = os.path.join(DATA_DIR, "city_dynamic_adjustments.json")
WINTER_USER_THRESHOLD = 0.60
WINTER_DEST_THRESHOLD = 0.55

W_FIZ = np.array([FIZIK_WEIGHTS[f]  for f in FIZIK_FEATURES],  dtype=float)
W_SOS = np.array([SOSYAL_WEIGHTS[f] for f in SOSYAL_FEATURES], dtype=float)


# ── Veri yükleme ──────────────────────────────────────────

def sehirleri_yukle() -> pd.DataFrame:
    path = MODEL_DATA_PATH if os.path.exists(MODEL_DATA_PATH) else os.path.join(DATA_DIR, "destinasyonlar.csv")
    df = pd.read_csv(path)
    df = _merge_quality_layer(df)
    df = _apply_dynamic_adjustments(df)
    return df


def _merge_quality_layer(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for feature in QUALITY_FEATURES:
        if feature not in out.columns:
            out[feature] = 0.70
    if not os.path.exists(SAFETY_DATA_PATH):
        return out
    with open(SAFETY_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = {city: vals for city, vals in data.items() if city != "_meta"}
    for idx, row in out.iterrows():
        values = rows.get(row["sehir"], {})
        for feature in QUALITY_FEATURES:
            if feature in values:
                out.at[idx, feature] = float(values[feature])
    return out


def _apply_dynamic_adjustments(df: pd.DataFrame) -> pd.DataFrame:
    if not os.path.exists(DYNAMIC_ADJUSTMENTS_PATH):
        return df
    with open(DYNAMIC_ADJUSTMENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    adjustments = data.get("cities", data)
    if not isinstance(adjustments, dict):
        return df
    out = df.copy()
    adjustable = FIZIK_FEATURES + SOSYAL_FEATURES + QUALITY_FEATURES
    for city, deltas in adjustments.items():
        if not isinstance(deltas, dict):
            continue
        mask = out["sehir"].eq(city)
        if not mask.any():
            continue
        for feature, delta in deltas.items():
            if feature in adjustable and feature in out.columns:
                out.loc[mask, feature] = np.clip(
                    out.loc[mask, feature].astype(float) + float(delta),
                    0.0,
                    1.0,
                )
    return out


# ── Vektör dönüşüm ────────────────────────────────────────

def fizik_vektore_cevir(deger_dict: dict) -> np.ndarray:
    return np.array([deger_dict.get(f, 0.0) for f in FIZIK_FEATURES], dtype=float)


def sosyal_vektore_cevir(deger_dict: dict) -> np.ndarray:
    return np.array([deger_dict.get(f, 0.0) for f in SOSYAL_FEATURES], dtype=float)


def vektore_cevir(deger_dict: dict) -> np.ndarray:
    """Geriye dönük uyumluluk — tam 13 boyutlu vektör."""
    return np.array([deger_dict.get(f, 0.0) for f in FEATURES], dtype=float)


# ── Benzerlik fonksiyonları ───────────────────────────────

def weighted_cosine(a: np.ndarray, b: np.ndarray, W: np.ndarray) -> float:
    aw, bw = a * W, b * W
    na, nb = np.linalg.norm(aw), np.linalg.norm(bw)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(aw, bw) / (na * nb))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Düz cosine — geriye dönük uyumluluk."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── Ana skor fonksiyonu ───────────────────────────────────

def dual_skor(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    s_fiz: np.ndarray,
    s_sos: np.ndarray,
    s_mevsim: float = None,
    u_mevsim: int = None,
) -> tuple[float, float, float]:
    """
    Çift vektör hybrid skoru.

    Döndürür: (toplam, skor_fizik, skor_sosyal)
    """
    cos_fiz = weighted_cosine(u_fiz, s_fiz, W_FIZ)
    cos_sos = weighted_cosine(u_sos, s_sos, W_SOS)

    # Mevsim soft penalty: yaz/kış uyumsuzluğunda fiziksel cosine düşer
    if u_mevsim is not None and s_mevsim is not None and s_mevsim != 2:
        if int(u_mevsim) != int(s_mevsim):
            cos_fiz *= MEVSIM_CARPAN

    skor_fiz = FIZIK_AGIRLIK  * cos_fiz
    skor_sos = SOSYAL_AGIRLIK * cos_sos
    return round(skor_fiz + skor_sos, 4), round(skor_fiz, 4), round(skor_sos, 4)


def _overlap_sparse(u_fiz, u_sos, s_fiz, s_sos):
    """Ortak dolu feature oranı + sparse ceza — dual vektör versiyonu."""
    u = np.concatenate([u_fiz, u_sos])
    s = np.concatenate([s_fiz, s_sos])
    dolu_u = u > 0.05
    dolu_s = s > 0.05
    ortak  = np.sum(dolu_u & dolu_s)
    toplam = np.sum(dolu_u | dolu_s)
    overlap = ortak / toplam if toplam > 0 else 0.0
    sparse  = min(np.sum(dolu_u) / len(u) * 2, 1.0)
    return overlap, sparse


def hybrid_skor(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    s_fiz: np.ndarray,
    s_sos: np.ndarray,
    s_mevsim: float = None,
    u_mevsim: int = None,
) -> float:
    """
    Tam hybrid skor: dual cosine + overlap + sparse.
    Tek float döndürür (öneri sıralaması için).
    """
    toplam, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim, u_mevsim)
    overlap, sparse = _overlap_sparse(u_fiz, u_sos, s_fiz, s_sos)
    return round(toplam * 0.80 + overlap * 0.12 + sparse * 0.08, 4)


# ── Güven skoru ───────────────────────────────────────────

def guven_skoru_hesapla(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    gosterilen: int = 0,
    u_mevsim: int = None,
) -> float:
    """Model güveni. MIN_FOTO dolmadan 0.0 döner."""
    if gosterilen < MIN_FOTO:
        return 0.0
    u = np.concatenate([u_fiz, u_sos])
    if np.sum(u > 0.05) < 3:
        return 0.0
    skorlar = [
        hybrid_skor(
            u_fiz, u_sos,
            satir[FIZIK_FEATURES].values.astype(float),
            satir[SOSYAL_FEATURES].values.astype(float),
            float(satir["mevsim"]) if "mevsim" in df.columns else None,
            u_mevsim,
        )
        for _, satir in df.iterrows()
    ]
    return max(skorlar)


# ── Tip tespiti ───────────────────────────────────────────

def tip_tespiti(u_fiz: np.ndarray, u_sos: np.ndarray, df: pd.DataFrame) -> str:
    """Kullanıcının hangi genel tipe uyduğunu bul."""
    tip_skorlari = {}
    for tip, sehirler in TIPLER.items():
        tip_df = df[df["sehir"].isin(sehirler)]
        if tip_df.empty:
            continue
        t_fiz = tip_df[FIZIK_FEATURES].mean().values.astype(float)
        t_sos = tip_df[SOSYAL_FEATURES].mean().values.astype(float)
        tip_skorlari[tip] = (
            FIZIK_AGIRLIK  * weighted_cosine(u_fiz, t_fiz, W_FIZ) +
            SOSYAL_AGIRLIK * weighted_cosine(u_sos, t_sos, W_SOS)
        )
    if not tip_skorlari:
        return "Genel"
    return max(tip_skorlari, key=tip_skorlari.get)


def _user_wants_winter(u_fiz: np.ndarray) -> bool:
    if "kis_spor" not in FIZIK_FEATURES:
        return False
    return float(u_fiz[FIZIK_FEATURES.index("kis_spor")]) > WINTER_USER_THRESHOLD


def _is_winter_destination(satir) -> bool:
    kis = float(satir["kis_spor"]) if "kis_spor" in satir else 0.0
    mevsim = int(float(satir["mevsim"])) if "mevsim" in satir else 2
    return kis >= WINTER_DEST_THRESHOLD or mevsim == 1


def _apply_winter_branch(sonuclar: list[dict], top_n: int, wants_winter: bool) -> list[dict]:
    normal = [item for item in sonuclar if not item.get("is_winter_candidate")]
    winter = [item for item in sonuclar if item.get("is_winter_candidate")]

    normal_top = normal[:top_n]
    if wants_winter and top_n <= 3 and winter:
        extra = dict(winter[0])
        extra["is_winter_extra"] = True
        extra["tip"] = "Kis ekstra"
        return normal_top + [extra]
    return normal_top


def _constraint_penalty(u_sos: np.ndarray, satir) -> float:
    """Survey-derived constraints should penalize mismatches, not only cosine-match."""
    penalty = 0.0
    if "fiyat" in SOSYAL_FEATURES and "fiyat" in satir:
        user_price = float(u_sos[SOSYAL_FEATURES.index("fiyat")])
        city_price = float(satir["fiyat"])
        if 0.05 < user_price < 0.40 and city_price > user_price:
            penalty += (city_price - user_price) * 0.40
    if "ulasim_kolayligi" in SOSYAL_FEATURES and "ulasim_kolayligi" in satir:
        user_transport = float(u_sos[SOSYAL_FEATURES.index("ulasim_kolayligi")])
        city_transport = float(satir["ulasim_kolayligi"])
        if user_transport >= 0.70 and city_transport < user_transport:
            penalty += (user_transport - city_transport) * 0.16
    if "sakin" in SOSYAL_FEATURES and "sakin" in satir:
        user_quiet = float(u_sos[SOSYAL_FEATURES.index("sakin")])
        city_quiet = float(satir["sakin"])
        city_lively = float(satir["eglence"]) if "eglence" in satir else 0.0
        if user_quiet >= 0.70 and city_quiet < user_quiet:
            penalty += (user_quiet - city_quiet) * 0.12
        if user_quiet >= 0.70 and city_lively >= 0.70:
            penalty += 0.05
    return float(min(penalty, 0.28))


def _quality_score(satir) -> float:
    score = 0.0
    total = 0.0
    for feature, weight in QUALITY_WEIGHTS.items():
        if feature in satir:
            score += float(satir[feature]) * float(weight)
            total += float(weight)
    return float(score / total) if total > 0 else 0.70


def _quality_penalty(satir, prefer_safety: bool = False) -> float:
    quality = _quality_score(satir)
    if prefer_safety:
        return max(0.0, 0.75 - quality) * 0.34
    return max(0.0, 0.55 - quality) * 0.12


# ── Öneri ────────────────────────────────────────────────

def oneri_yap(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    gidilen_sehirler: list = None,
    top_n: int = 3,
    model=None,
    aciklamalar: dict = None,
    u_mevsim: int = None,
    prefer_safety: bool = False,
    shuffle: bool = False,
) -> list[dict]:
    """Top-N şehir öner. Model varsa onu, yoksa hybrid skor kullan."""
    gidilen = gidilen_sehirler or []
    wants_winter = _user_wants_winter(u_fiz)

    if model is not None:
        return _maybe_shuffle_results(
            _model_ile_oner(
                u_fiz, u_sos, df, gidilen, top_n, model, u_mevsim, wants_winter, prefer_safety
            ),
            shuffle,
        )

    en_iyi_tip = tip_tespiti(u_fiz, u_sos, df)
    tip_sehirleri = TIPLER.get(en_iyi_tip, [])

    sonuclar = []
    for _, satir in df.iterrows():
        if satir["sehir"] in gidilen:
            continue
        s_fiz    = satir[FIZIK_FEATURES].values.astype(float)
        s_sos    = satir[SOSYAL_FEATURES].values.astype(float)
        s_mevsim = float(satir["mevsim"]) if "mevsim" in df.columns else None

        skor_top, skor_fiz, skor_sos = dual_skor(
            u_fiz, u_sos, s_fiz, s_sos, s_mevsim, u_mevsim
        )
        overlap, sparse = _overlap_sparse(u_fiz, u_sos, s_fiz, s_sos)
        skor = skor_top * 0.80 + overlap * 0.12 + sparse * 0.08
        tip_bonusu = 0.05 if satir["sehir"] in tip_sehirleri else 0.0
        constraint_penalty = _constraint_penalty(u_sos, satir)
        quality = _quality_score(satir)
        quality_penalty = _quality_penalty(satir, prefer_safety)

        aciklama_raw = (aciklamalar or {}).get(satir["sehir"], "")
        final_skor = skor + tip_bonusu - constraint_penalty - quality_penalty
        if prefer_safety:
            final_skor = (final_skor * 0.82) + (quality * 0.18)
        sonuclar.append({
            "sehir":       satir["sehir"],
            "aciklama_raw": aciklama_raw,
            "aciklama":    (aciklama_raw.get("TR", "") if isinstance(aciklama_raw, dict)
                            else aciklama_raw),
            "skor":        round(float(max(min(final_skor, 0.99), 0.0)), 3),
            "skor_fizik":  skor_fiz,
            "skor_sosyal": skor_sos,
            "tip":         en_iyi_tip,
            "vektor_fiz":  s_fiz,
            "vektor_sos":  s_sos,
            "is_winter_candidate": _is_winter_destination(satir),
            "is_winter_extra": False,
            "constraint_penalty": round(constraint_penalty, 3),
            "quality_score": round(quality, 3),
            "quality_penalty": round(quality_penalty, 3),
            "fark":        _fark_hesapla(u_fiz, u_sos, s_fiz, s_sos),
        })

    sonuclar.sort(key=lambda x: x["skor"], reverse=True)
    return _maybe_shuffle_results(_apply_winter_branch(sonuclar, top_n, wants_winter), shuffle)


def _maybe_shuffle_results(sonuclar: list[dict], shuffle: bool) -> list[dict]:
    out = list(sonuclar)
    if shuffle and len(out) > 1:
        random.shuffle(out)
    return out


def _model_ile_oner(u_fiz, u_sos, df, gidilen, top_n, model, u_mevsim, wants_winter, prefer_safety=False):
    sonuclar = []
    for _, satir in df.iterrows():
        if satir["sehir"] in gidilen:
            continue
        s_fiz = satir[FIZIK_FEATURES].values.astype(float)
        s_sos = satir[SOSYAL_FEATURES].values.astype(float)
        girdi = np.concatenate([u_fiz, u_sos, s_fiz, s_sos]).reshape(1, -1)
        skor  = model.predict_proba(girdi)[0][1]

        # Mevsim penalty modele de uygula
        s_mevsim = float(satir["mevsim"]) if "mevsim" in df.columns else None
        if u_mevsim is not None and s_mevsim is not None and s_mevsim != 2:
            if int(u_mevsim) != int(s_mevsim):
                skor *= MEVSIM_CARPAN
        constraint_penalty = _constraint_penalty(u_sos, satir)
        quality = _quality_score(satir)
        quality_penalty = _quality_penalty(satir, prefer_safety)
        skor = max(float(skor) - constraint_penalty - quality_penalty, 0.0)
        if prefer_safety:
            skor = (skor * 0.82) + (quality * 0.18)

        _, skor_fiz, skor_sos = dual_skor(u_fiz, u_sos, s_fiz, s_sos, s_mevsim, u_mevsim)
        sonuclar.append({
            "sehir":       satir["sehir"],
            "skor":        round(float(skor), 3),
            "skor_fizik":  skor_fiz,
            "skor_sosyal": skor_sos,
            "tip":         tip_tespiti(u_fiz, u_sos, df),
            "vektor_fiz":  s_fiz,
            "vektor_sos":  s_sos,
            "is_winter_candidate": _is_winter_destination(satir),
            "is_winter_extra": False,
            "constraint_penalty": round(constraint_penalty, 3),
            "quality_score": round(quality, 3),
            "quality_penalty": round(quality_penalty, 3),
            "fark":        _fark_hesapla(u_fiz, u_sos, s_fiz, s_sos),
        })
    sonuclar.sort(key=lambda x: x["skor"], reverse=True)
    return _apply_winter_branch(sonuclar, top_n, wants_winter)


def _fark_hesapla(u_fiz, u_sos, s_fiz, s_sos) -> dict:
    """Kara kutu açma: hangi feature'lar bu öneriyi yaptı? İki grup ayrı."""
    fiz_carpim = u_fiz * s_fiz * W_FIZ
    sos_carpim = u_sos * s_sos * W_SOS
    toplam = fiz_carpim.sum() + sos_carpim.sum()
    if toplam == 0:
        return {}

    fiz_katki = {FIZIK_FEATURES[i]: round(float(fiz_carpim[i] / toplam), 3)
                 for i in range(len(FIZIK_FEATURES))}
    sos_katki = {SOSYAL_FEATURES[i]: round(float(sos_carpim[i] / toplam), 3)
                 for i in range(len(SOSYAL_FEATURES))}

    # Tüm katkıları birleştir, top-4 döndür
    tum = {**fiz_katki, **sos_katki}
    return dict(sorted(tum.items(), key=lambda x: x[1], reverse=True)[:4])


# ── Kullanıcı vektörü güncelleme ─────────────────────────

def kullanici_vektoru_guncelle(
    mevcut: np.ndarray,
    secilen: np.ndarray,
    ogrenme_hizi: float = 0.3,
) -> np.ndarray:
    """Foto seçimi sonrası EMA güncellemesi."""
    yeni = mevcut + ogrenme_hizi * (secilen - mevcut)
    return np.clip(yeni, 0.0, 1.0)


def hatali_tahminden_ogren(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    yanlis_fiz: np.ndarray,
    yanlis_sos: np.ndarray,
    dogru_fiz: np.ndarray,
    dogru_sos: np.ndarray,
    ogrenme_hizi: float = 0.4,
) -> tuple[np.ndarray, np.ndarray]:
    """Yanlış şehirden uzaklaş, doğru şehre yaklaş — iki vektör için."""
    yeni_fiz = u_fiz - ogrenme_hizi * (yanlis_fiz - u_fiz) * 0.5
    yeni_fiz = yeni_fiz + ogrenme_hizi * (dogru_fiz - u_fiz)

    yeni_sos = u_sos - ogrenme_hizi * (yanlis_sos - u_sos) * 0.5
    yeni_sos = yeni_sos + ogrenme_hizi * (dogru_sos - u_sos)

    return np.clip(yeni_fiz, 0.0, 1.0), np.clip(yeni_sos, 0.0, 1.0)


# ── Adaptive soru seçimi ─────────────────────────────────

def adaptif_soru_sec(
    u_fiz: np.ndarray,
    u_sos: np.ndarray,
    df: pd.DataFrame,
    turlar: list,
    gosterilmis_idx: set,
    u_mevsim: int = None,
    user_vibe_emb: np.ndarray | None = None,
    photo_embs: dict | None = None,
    region_embs: dict | None = None,
) -> int | None:
    """Sıradaki fotoğraf çiftini seç.

    user_vibe_emb + photo_embs + region_embs verilirse BALD (embedding uzayı).
    Verilmezse heuristic info-gain (özellik uzayı).
    """
    return select_next_pair(
        u_fiz, u_sos, df, turlar, gosterilmis_idx,
        user_vibe_emb=user_vibe_emb,
        photo_embs=photo_embs,
        region_embs=region_embs,
    )


# ── Model yükleme ─────────────────────────────────────────

def model_yukle():
    """Backward-compatible wrapper for the active joblib-only ranker loader."""
    from model.recommend import load_ranker
    return load_ranker()
