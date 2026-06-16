"""
Tek kaynak: feature listeler, ağırlıklar, sabitler.
predict.py / train.py / app/main.py buradan import eder.

İKİ VEKTÖR MİMARİSİ:
  Fiziksel  → şehrin gözlenebilir/coğrafi/kültürel sunumu
  Sosyolojik → kullanıcının sosyal ve pratik tercihleri
"""

import json
from pathlib import Path

# ── Fiziksel Vektör (8 boyut) ─────────────────────────────
FIZIK_FEATURES = [
    "deniz", "doga", "tarih", "kultur",
    "doga_spor", "su_spor", "hava_spor", "kis_spor",
]

FIZIK_WEIGHTS = {
    "deniz":     1.0,
    "doga":      1.0,
    "tarih":     1.15,
    "kultur":    1.10,
    "doga_spor": 1.2,
    "su_spor":   1.2,
    "hava_spor": 1.4,
    "kis_spor":  1.4,
}

# ── Sosyolojik / pratik Vektör (5 boyut) ──────────────────
SOSYAL_FEATURES = [
    "eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat",
]

SOSYAL_WEIGHTS = {
    "eglence":          1.0,
    "sakin":            1.0,
    "yemek":            1.1,
    "ulasim_kolayligi": 0.9,
    "fiyat":            0.8,
}

# ── Birleşik liste (geriye dönük uyumluluk / CSV okuma) ───
FEATURES = FIZIK_FEATURES + SOSYAL_FEATURES

# ── Final skor katkı oranları ─────────────────────────────
FIZIK_AGIRLIK  = 0.55
SOSYAL_AGIRLIK = 0.45

# ── Mevsim soft penalty ───────────────────────────────────
# Kullanıcı tercihiyle uyumsuz mevsimli şehirlerin fiziksel cosine'i bu katsayıyla çarpılır.
# mevsim değerleri: 0=yaz, 1=kış, 2=dört mevsim (ceza yok)
MEVSIM_CARPAN = 0.35

EXTRA_FEATURES = ["mevsim"]  # fiyat artık SOSYAL_FEATURES'da

# ── Kalite / risk katmanı ─────────────────────────────────
# Ana 13 boyutlu tercih vektörüne katılmaz; skor sonrası quality penalty /
# güvenlik önceliği için ayrı katman olarak kullanılır.
QUALITY_FEATURES = [
    "safety",
    "pollution",
    "livability",
    "health_risk",
]

QUALITY_WEIGHTS = {
    "safety": 0.40,
    "pollution": 0.25,
    "livability": 0.25,
    "health_risk": 0.10,
}

# ── Adaptif foto döngüsü ──────────────────────────────────
MIN_FOTO    = 5
MAX_FOTO    = 10
GUVEN_ESIGI = 0.88

# ── Model eğitimi ─────────────────────────────────────────
MIN_TRAIN_N = 30
CV_FOLDS    = 5

# ── Bölge havuzları ──────────────────────────────────────
_REGIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "regions.json"


def _load_regions_from_data() -> dict[str, list[str]]:
    with open(_REGIONS_FILE, "r", encoding="utf-8") as f:
        regions = json.load(f)
    return {
        str(region["id"]): list(region.get("sub_destinations", []))
        for region in regions
    }


REGIONS = _load_regions_from_data()

# Geriye dönük uyumluluk: mevcut öneri kodu bu adı kullanıyor.
TIPLER = REGIONS
