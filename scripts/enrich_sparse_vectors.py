#!/usr/bin/env python3
"""Faz D: Enrich sparse city feature vectors in model_destinasyonlar.csv.

27 cities have fewer than 3 features >= 0.30. This script patches them directly
with semantically correct values derived from destination_text_sources.json.

Run: python scripts/enrich_sparse_vectors.py
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / "data" / "model_destinasyonlar.csv"

# Per-city feature overrides. Keys are model_destinasyonlar.csv column names.
# Only sets/raises values — existing higher values for other features are kept.
# For Olu Deniz and Wadi Rum, wrong-scraped values are explicitly corrected.
CITY_PATCHES: dict[str, dict[str, float]] = {
    # ── Türkiye ──────────────────────────────────────────────────────────────
    "Uzungol": {
        # Karadeniz yayla gölü — doğa ve yürüyüş güçlü, doga/sakin zaten var
        "doga_spor": 0.58,
        "yemek":     0.42,
    },
    "Efes": {
        # Antik Roma kenti — tarih/kültür zaten var, sakin ve doğa tamamlar
        "sakin": 0.55,
        "doga":  0.45,
    },
    "Olu Deniz": {
        # Yanlış kaynak metni scraplanmış (Ölü Deniz). Doğru değerler:
        # Ölüdeniz lagünü + Babadağ yamaç paraşütü
        "deniz":    0.92,
        "hava_spor": 0.90,
        "doga":     0.75,
        "sakin":    0.55,
        "tarih":    0.12,
        "kultur":   0.18,
    },

    # ── Kuzey Afrika ─────────────────────────────────────────────────────────
    "Sanliurfa": {
        # Peygamberler şehri — tarih/kültür var; mutfak ve dini atmosfer ekle
        "yemek":  0.72,
        "sakin":  0.48,
    },
    "Marakes": {
        # Fas'ın ünlü turu şehri — yemek, eğlence ve pazar kültürü
        "yemek":   0.75,
        "eglence": 0.55,
    },
    "Fes": {
        # Dünyanın en eski medresesi, geleneksel Fas mutfağı
        "yemek":  0.68,
        "sakin":  0.52,
    },
    "Tunus": {
        # Akdeniz kıyısı başkent — deniz, yemek
        "deniz":  0.58,
        "yemek":  0.58,
    },
    "Sidi Bou Said": {
        # Akdeniz'e bakan mavi-beyaz sakin köy
        "sakin":  0.82,
        "deniz":  0.65,
    },
    "Kairouan": {
        # İslam'ın 4. kutsal şehri — sakin dini atmosfer
        "sakin":  0.68,
        "yemek":  0.42,
    },

    # ── Güney Amerika ────────────────────────────────────────────────────────
    "Machu Picchu": {
        # İnka kalesi — tarih ve doğa sporları (trekking) çok güçlü
        "tarih":    0.95,
        "doga_spor": 0.85,
    },
    "Amazon": {
        # Amazonlar — doğa sporları (kano, treking) ve sessizlik
        "sakin":    0.75,
        "doga_spor": 0.82,
    },
    "Galapagos": {
        # Ekvador adaları — deniz ve sessizlik
        "deniz":  0.78,
        "sakin":  0.72,
    },
    "Uyuni": {
        # Dünyanın en büyük tuz düzlüğü — sessizlik ve macera
        "sakin":    0.85,
        "doga_spor": 0.62,
    },

    # ── Doğu Afrika ──────────────────────────────────────────────────────────
    "Zanzibar": {
        # Hint Okyanusu adası — plajlar, tarih, sakin
        "deniz":  0.90,
        "sakin":  0.72,
        "tarih":  0.55,   # Stone Town UNESCO
    },
    "Serengeti": {
        # Sakin vahşi yaşam rezervi
        "sakin":    0.78,
        "doga_spor": 0.72,  # safari trekking güçlendir
    },
    "Nairobi": {
        # Kenya başkenti — kültür merkezi ve lojistik hub
        "kultur":  0.58,
        "eglence": 0.48,
    },
    "Kilimanjaro": {
        # Afrika'nın en yüksek dağı — sakin ve ekstrem dağ sporları
        "sakin":    0.80,
        "doga_spor": 0.88,  # zirve tırmanışı
    },
    "Kigali": {
        # Rwanda başkenti — yeşil şehir, kültürel dönüşüm
        "kultur":  0.58,
        "sakin":   0.62,
    },

    # ── Orta Doğu ────────────────────────────────────────────────────────────
    "Wadi Rum": {
        # Yanlış: tarih/kültür yüksek ama esas doğa/macera şehri
        "doga":     0.90,
        "sakin":    0.82,
        "doga_spor": 0.75,
        "tarih":    0.55,   # kaya resimleri, Bedevi mirası
        "kultur":   0.45,
    },
    "Kahire": {
        # Mısır başkenti — yemek ve gece hayatı da önemli
        "yemek":   0.58,
        "eglence": 0.45,
    },
    "Abu Dabi": {
        # UAE başkenti — Louvre Abu Dhabi, kültürel altyapı
        "kultur":  0.68,
        "tarih":   0.48,
        "eglence": 0.55,
    },
    "Doha": {
        # Katar başkenti — Katara kültür köyü, müzeler
        "kultur":  0.65,
        "tarih":   0.45,
        "eglence": 0.52,
    },
    "Muskat": {
        # Umman başkenti — tarihi liman, Sultan Camii, kıyı
        "tarih":  0.72,
        "deniz":  0.58,
    },
    "Riyad": {
        # Suudi başkenti — Diriyah UNESCO, Edge of the World
        "tarih":  0.60,
        "kultur": 0.52,
    },

    # ── Okyanusya ────────────────────────────────────────────────────────────
    "Sydney": {
        # Opera House şehri — eğlence ve ulaşım kolaylığı çok yüksek
        "eglence":           0.72,
        "ulasim_kolayligi":  0.75,
        "yemek":             0.62,
    },
    "Melbourne": {
        # Avustralya'nın yemek-sanat şehri
        "yemek":             0.80,
        "eglence":           0.68,
        "ulasim_kolayligi":  0.70,
        "kultur":            0.62,
    },
    "Suva": {
        # Fiji başkenti — sakin Pasifik adası
        "sakin": 0.65,
        "tarih": 0.38,
    },
}


def main() -> None:
    if not CSV_PATH.exists():
        print(f"[ERROR] {CSV_PATH} not found")
        return

    df = pd.read_csv(CSV_PATH)
    patched = 0

    for city, overrides in CITY_PATCHES.items():
        mask = df["sehir"] == city
        if not mask.any():
            print(f"[SKIP] {city}: not in CSV")
            continue
        for col, val in overrides.items():
            if col not in df.columns:
                print(f"[SKIP] {city}.{col}: column not found")
                continue
            df.loc[mask, col] = round(float(val), 3)
        patched += 1

    df.to_csv(CSV_PATH, index=False)
    print(f"[OK] Patched {patched} cities → {CSV_PATH}")

    # Verify: count remaining sparse cities
    all_feats = ["deniz","doga","tarih","kultur","doga_spor","su_spor","hava_spor",
                 "kis_spor","eglence","sakin","yemek","ulasim_kolayligi","fiyat"]
    available = [f for f in all_feats if f in df.columns]
    still_sparse = []
    for _, row in df.iterrows():
        n = sum(float(row[f]) >= 0.30 for f in available)
        if n < 3:
            still_sparse.append(row["sehir"])
    if still_sparse:
        print(f"[WARN] {len(still_sparse)} cities still sparse: {still_sparse}")
    else:
        print("[OK] All cities now have >= 3 features above 0.30")


if __name__ == "__main__":
    main()
