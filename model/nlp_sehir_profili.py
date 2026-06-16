"""
NLP ile şehir feature vektörlerini otomatik üret.
TF-IDF tabanlı — her feature için keyword grubu tanımlanır,
metindeki ağırlıklı frekansa göre 0-1 skoru hesaplanır.
Sonuç: destinasyonlar.csv (manuel değil, veriden üretilmiş)

ÇALIŞTIRMA:
    python model/nlp_sehir_profili.py
"""

import json
import os
import re
import sys
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.append(os.path.dirname(__file__))
from config import FEATURES as CFG_FEATURES

# ── Türkçe stopwords ─────────────────────────────────────
STOPWORDS = {
    "ve", "ile", "bir", "bu", "da", "de", "ki", "en", "için",
    "olan", "olan", "olarak", "gibi", "çok", "daha", "her",
    "hem", "ya", "veya", "ama", "fakat", "ancak", "ile", "çok",
    "kadar", "sonra", "önce", "üzere", "arasında", "olan",
    "edilir", "edilmektedir", "mevcuttur", "bulunur", "vardır",
}

# ── Feature → Türkçe anahtar kelimeler ───────────────────
FEATURE_KEYWORDS = {
    "deniz": [
        "deniz", "plaj", "koy", "kumsal", "sahil", "yüzme",
        "turkuaz", "mavi", "dalga", "kıyı", "marina", "liman",
        "tekne", "yat", "lagün", "körfez",
    ],
    "doga": [
        "dağ", "orman", "yayla", "göl", "şelale", "doğa",
        "yeşil", "vadi", "kanyon", "tepe", "zirve", "buzul",
        "ekosistem", "ağaç", "manzara", "dere",
    ],
    "tarih": [
        "tarihi", "antik", "müze", "harabe", "kale", "osmanlı",
        "bizans", "arkeoloji", "kalıntı", "mozaik", "manastır",
        "kilise", "cami", "medrese", "yapı", "dönem", "saray",
    ],
    "kultur": [
        "kültür", "festival", "gelenek", "sanat", "çarşı",
        "yerel", "otantik", "zanaat", "el sanatı", "geleneksel",
        "töre", "köy", "halk", "etnik", "dini", "kutsal",
    ],
    "eglence": [
        "eğlence", "bar", "kulüp", "gece", "parti", "konser",
        "aquapark", "lunapark", "disko", "canlı müzik", "aktif",
        "alışveriş", "mağaza", "restoran", "kafe",
    ],
    "sakin": [
        "sakin", "huzurlu", "sessiz", "tenha", "ıssız",
        "dinlendirici", "bakir", "uzak", "uzlet", "doğal",
        "keşfedilmemiş", "gürültüsüz", "az kalabalık",
    ],
    "doga_spor": [
        "trekking", "kamp", "yürüyüş", "atv", "dağcılık",
        "at binme", "macera", "patika", "zirve", "bisiklet",
        "doğa sporları", "hiking",
    ],
    "su_spor": [
        "sörf", "dalış", "rafting", "tekne turu", "kano",
        "su kayağı", "snorkeling", "jet ski", "rüzgar sörfü",
        "sualtı", "su sporları",
    ],
    "hava_spor": [
        "balon", "paraşüt", "yamaç paraşütü", "hava sporları",
        "uçuş", "atlama", "gökyüzü",
    ],
    "kis_spor": [
        "kayak", "snowboard", "kar", "kış", "pist", "kızak",
        "kayakçı", "kış sporları", "kar sporları", "teleferik",
    ],
    "yemek": [
        "yemek", "lezzet", "kebap", "mutfak", "restoran",
        "baklava", "meze", "kahvaltı", "zeytinyağlı", "balık",
        "hamsi", "köfte", "dolma", "tatlı", "gastronomi",
    ],
    "ulasim_kolayligi": [
        "toplu taşıma", "tramvay", "metro", "otobüs", "dolmuş",
        "yürüyerek", "yürüme mesafesi", "merkezi", "araçsız",
        "kolay ulaşım", "ulaşım", "yakın", "kompakt", "şehir içi",
    ],
    "fiyat": [
        "pahalı", "lüks", "yüksek fiyat", "ekonomik", "uygun",
        "bütçe", "ucuz", "hesaplı", "karşılanabilir",
    ],
}

# Fiyat için özel işleme (negatif-pozitif)
PAHALI_KELIMELER = {"pahalı", "lüks", "yüksek fiyat", "yüksektir"}
UCUZ_KELIMELER   = {"ekonomik", "uygun", "bütçe", "ucuz", "hesaplı", "dostudur"}

PHYSICAL_FEATURES = [
    "deniz", "doga", "tarih", "kultur",
    "doga_spor", "su_spor", "hava_spor", "kis_spor",
]
SOCIOLOGICAL_FEATURES = ["eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat"]
ALL_FEATURES = PHYSICAL_FEATURES + SOCIOLOGICAL_FEATURES


def temizle(metin: str) -> str:
    metin = metin.lower()
    metin = re.sub(r"[^\w\s]", " ", metin)
    return metin


def fiyat_skoru(metin: str) -> float:
    """
    Fiyat özel işleme:
    pahalı/lüks kelimeleri → yüksek fiyat (1.0'a yakın)
    ucuz/ekonomik → düşük fiyat (0.0'a yakın)
    """
    metin_lower = metin.lower()
    pahali = sum(metin_lower.count(k) for k in PAHALI_KELIMELER)
    ucuz   = sum(metin_lower.count(k) for k in UCUZ_KELIMELER)
    if pahali + ucuz == 0:
        return 0.5  # bilinmiyor → orta
    return pahali / (pahali + ucuz)


def tfidf_skor(metinler: dict, feature: str) -> dict:
    """
    TF-IDF ile her şehir için feature skoru hesapla.
    Keyword'ler feature'ı temsil eden "sözde belge" oluşturur.
    """
    keywords = FEATURE_KEYWORDS[feature]
    pseudo_doc = " ".join(keywords * 3)  # keyword dokümanı

    sehirler = list(metinler.keys())
    belgeler = [temizle(metinler[s]) for s in sehirler]
    belgeler.append(temizle(pseudo_doc))

    vect = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
        stop_words=list(STOPWORDS)
    )
    tfidf_matrix = vect.fit_transform(belgeler)

    # Her şehrin pseudo_doc ile cosine similarity'si
    from sklearn.metrics.pairwise import cosine_similarity as cs
    pseudo_idx = len(sehirler)
    skorlar = cs(
        tfidf_matrix[:-1],      # şehirler
        tfidf_matrix[pseudo_idx]  # pseudo doc
    ).flatten()

    return {sehirler[i]: float(skorlar[i]) for i in range(len(sehirler))}


def normalize(degerler: dict, taban: float = 0.1, tavan: float = 0.95) -> dict:
    """
    Yumuşak normalizasyon:
    - Ham değer 0 olsa bile çıktı 'taban' (varsayılan 0.1) — feature tamamen sıfırlanmaz.
    - En yüksek şehir 'tavan' (0.95) — %100 sahte match'i engeller.
    - Min-max'ın bilgi-yıkıcı etkisini azaltır; ham skor bilgisi korunur.
    """
    vals = list(degerler.values())
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return {k: round(taban + (tavan - taban) / 2, 3) for k in degerler}
    olcek = tavan - taban
    return {
        k: round(taban + olcek * (v - mn) / (mx - mn), 3)
        for k, v in degerler.items()
    }


def percentile_rank(degerler: dict, taban: float = 0.1, tavan: float = 0.95) -> dict:
    """
    Sıralama tabanlı normalizasyon (outlier'a dayanıklı).
    En düşük şehir 'taban', en yüksek 'tavan', aralarda eşit aralıklı.
    """
    sirali = sorted(degerler.items(), key=lambda x: x[1])
    n = len(sirali)
    if n == 1:
        return {sirali[0][0]: round((taban + tavan) / 2, 3)}
    olcek = tavan - taban
    return {
        ad: round(taban + olcek * i / (n - 1), 3)
        for i, (ad, _) in enumerate(sirali)
    }


def sehir_profillerini_uret(metinler: dict) -> pd.DataFrame:
    """
    Tüm şehirler için feature vektörlerini NLP ile üret.
    """
    print("[NLP] Şehir profilleri üretiliyor...")
    sehirler = list(metinler.keys())
    sonuclar = {s: {} for s in sehirler}

    for feature in ALL_FEATURES:
        if feature == "fiyat":
            # Fiyat özel hesaplama
            ham = {s: fiyat_skoru(metinler[s]) for s in sehirler}
            norm = {s: round(ham[s], 3) for s in sehirler}
        else:
            # TF-IDF cosine similarity
            ham  = tfidf_skor(metinler, feature)
            norm = normalize(ham)

        for s in sehirler:
            sonuclar[s][feature] = norm[s]

        vals = [norm[s] for s in sehirler]
        print(f"  {feature:12s} → min:{min(vals):.2f} max:{max(vals):.2f} "
              f"ort:{sum(vals)/len(vals):.2f}")

    # Mevsim: metinden çıkar
    MEVSIM_KEYWORDS = {
        0: ["yaz", "yüzme", "plaj", "güneş", "sıcak", "deniz"],
        1: ["kış", "kar", "kayak", "soğuk", "kış sporları"],
        2: ["dört mevsim", "her mevsim", "yıl boyu", "4 mevsim"],
    }
    for s in sehirler:
        metin = metinler[s].lower()
        skorlar_mevsim = {
            m: sum(metin.count(k) for k in kws)
            for m, kws in MEVSIM_KEYWORDS.items()
        }
        sonuclar[s]["mevsim"] = max(skorlar_mevsim, key=skorlar_mevsim.get)

    df = pd.DataFrame(sonuclar).T.reset_index()
    df.columns = ["sehir"] + [c for c in df.columns if c != "index"]

    # Sütun sırası
    sutunlar = ["sehir"] + PHYSICAL_FEATURES + SOCIOLOGICAL_FEATURES + ["mevsim"]
    df = df[sutunlar]
    return df


def main():
    # Metin verisini yükle
    metin_yolu = os.path.join(os.path.dirname(__file__), "..", "data", "sehir_metinleri.json")
    with open(metin_yolu, "r", encoding="utf-8") as f:
        metinler = json.load(f)

    print(f"[NLP] {len(metinler)} şehir yüklendi")

    # Profil üret
    df = sehir_profillerini_uret(metinler)

    # Kaydet
    cikti = os.path.join(os.path.dirname(__file__), "..", "data", "destinasyonlar.csv")
    df.to_csv(cikti, index=False)
    print(f"\n[NLP] Kaydedildi: {cikti}")
    print("\nÖrnek çıktı (ilk 5 şehir):")
    print(df.head().to_string(index=False))

    # Hangi şehir hangi feature'da en yüksek?
    print("\n[NLP] Feature başına en yüksek şehir:")
    for f in ALL_FEATURES:
        if f in df.columns:
            en_iyi = df.loc[df[f].idxmax(), "sehir"]
            skor   = df[f].max()
            print(f"  {f:12s}: {en_iyi} ({skor:.3f})")


if __name__ == "__main__":
    main()
