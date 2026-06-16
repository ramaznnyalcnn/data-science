"""Build destination vectors and hidden summaries from the ASCII catalog.

Inputs:
- data/destinasyonlar.csv
- data/sehir_metinleri.json

Outputs:
- data/destinasyonlar.csv        (fills L1/L2 score columns)
- data/model_destinasyonlar.csv  (8+5 model-ready vectors)
- data/cities.json
- data/regions.json
- data/vector_quality_report.md
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CATALOG_PATH = DATA / "destinasyonlar.csv"
TEXT_PATH = DATA / "sehir_metinleri.json"
MODEL_PATH = DATA / "model_destinasyonlar.csv"
CITIES_PATH = DATA / "cities.json"
REGIONS_PATH = DATA / "regions.json"
REPORT_PATH = DATA / "vector_quality_report.md"
HIDDEN_SUMMARIES_PATH = DATA / "hidden_summaries.json"
DESCRIPTION_PATH = DATA / "sehir_aciklamalari.json"
TEXT_SOURCE_PATH = DATA / "destination_text_sources.json"

L1_COLUMNS = [
    "l1_deniz",
    "l1_doga",
    "l1_tarih",
    "l1_eglence",
    "l1_sakin",
    "l1_sehir_hayati",
    "l1_macera",
    "l1_luks",
]
L2_COLUMNS = [
    "l2_kultur",
    "l2_su_spor",
    "l2_hava_spor",
    "l2_doga_spor",
    "l2_yemek",
    "l2_fotografik",
    "kis_spor",
]
SCORE_COLUMNS = L1_COLUMNS + L2_COLUMNS

PHYSICAL = [
    "deniz",
    "doga",
    "tarih",
    "kultur",
    "doga_spor",
    "su_spor",
    "hava_spor",
    "kis_spor",
]
SOCIOLOGICAL = ["eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat"]

CHAR_MAP = str.maketrans(
    {
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
        "â": "a",
        "Â": "A",
        "î": "i",
        "Î": "I",
        "û": "u",
        "Û": "U",
        "é": "e",
        "É": "E",
        "è": "e",
        "È": "E",
        "ê": "e",
        "Ê": "E",
        "á": "a",
        "Á": "A",
        "à": "a",
        "À": "A",
        "ã": "a",
        "Ã": "A",
        "ó": "o",
        "Ó": "O",
        "ô": "o",
        "Ô": "O",
        "õ": "o",
        "Õ": "O",
        "ú": "u",
        "Ú": "U",
        "ñ": "n",
        "Ñ": "N",
        "ø": "o",
        "Ø": "O",
        "ō": "o",
        "Ō": "O",
    }
)

KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "l1_deniz": [
        ("deniz", 1.0),
        ("plaj", 1.0),
        ("sahil", 0.9),
        ("koy", 0.9),
        ("ada", 0.8),
        ("okyanus", 1.0),
        ("lagun", 1.0),
        ("marina", 0.8),
        ("tekne", 0.7),
        ("yat", 0.7),
        ("kiyi", 0.8),
        ("resort", 0.6),
    ],
    "l1_doga": [
        ("doga", 1.0),
        ("dag", 1.0),
        ("orman", 1.0),
        ("gol", 0.9),
        ("vadi", 0.9),
        ("selale", 0.9),
        ("yayla", 1.0),
        ("milli park", 1.0),
        ("buzul", 1.0),
        ("safari", 0.9),
        ("volkan", 0.8),
        ("canyon", 0.8),
        ("kanyon", 0.8),
        ("park", 0.5),
    ],
    "l1_tarih": [
        ("tarih", 1.0),
        ("tarihi", 1.0),
        ("antik", 1.0),
        ("arkeoloji", 1.0),
        ("unesco", 0.9),
        ("kale", 0.8),
        ("tapinak", 0.9),
        ("saray", 0.8),
        ("katedral", 0.8),
        ("kilise", 0.7),
        ("cami", 0.7),
        ("muze", 0.7),
        ("harabe", 0.9),
        ("kalinti", 0.9),
        ("roma", 0.8),
        ("osmanli", 0.7),
        ("medeniyet", 0.7),
    ],
    "l1_eglence": [
        ("eglence", 1.0),
        ("gece hayati", 1.0),
        ("bar", 0.9),
        ("kulup", 0.9),
        ("festival", 0.8),
        ("konser", 0.8),
        ("canli", 0.5),
        ("alisveris", 0.7),
        ("restoran", 0.5),
        ("tema park", 0.8),
        ("dotonbori", 0.8),
    ],
    "l1_sakin": [
        ("sakin", 1.0),
        ("huzurlu", 1.0),
        ("sessiz", 0.9),
        ("uzak", 0.7),
        ("bakir", 0.8),
        ("tenha", 0.9),
        ("kasaba", 0.6),
        ("ada", 0.5),
        ("koy", 0.6),
        ("retreat", 0.9),
        ("wellness", 0.7),
    ],
    "l1_sehir_hayati": [
        ("sehir", 1.0),
        ("metropol", 1.0),
        ("metro", 0.9),
        ("merkez", 0.8),
        ("finans", 0.8),
        ("alisveris", 0.7),
        ("restoran", 0.7),
        ("galeri", 0.6),
        ("ulasim", 0.9),
        ("havalimani", 0.8),
        ("tren", 0.7),
        ("liman", 0.6),
        ("capital", 0.6),
        ("baskent", 0.8),
    ],
    "l1_macera": [
        ("macera", 1.0),
        ("trekking", 1.0),
        ("hiking", 1.0),
        ("dagcilik", 1.0),
        ("rafting", 0.9),
        ("dalis", 0.8),
        ("safari", 1.0),
        ("kayak", 0.9),
        ("snowboard", 0.9),
        ("kamp", 0.8),
        ("zipline", 0.7),
        ("atv", 0.8),
        ("parasutu", 0.9),
    ],
    "l1_luks": [
        ("luks", 1.0),
        ("pahali", 1.0),
        ("premium", 1.0),
        ("resort", 0.9),
        ("villa", 0.8),
        ("marina", 0.7),
        ("yat", 0.8),
        ("balayi", 0.8),
        ("butik otel", 0.6),
        ("otel", 0.4),
        ("fine dining", 0.8),
        ("konfor", 0.7),
    ],
    "l2_kultur": [
        ("kultur", 1.0),
        ("kulturel", 1.0),
        ("sanat", 1.0),
        ("galeri", 0.9),
        ("muzik", 0.7),
        ("tiyatro", 0.8),
        ("yerel", 0.8),
        ("gelenek", 0.9),
        ("el sanat", 0.9),
        ("mimari", 0.8),
        ("festival", 0.7),
        ("otantik", 0.8),
        ("pazar", 0.6),
    ],
    "l2_su_spor": [
        ("dalis", 1.0),
        ("snorkel", 1.0),
        ("sorf", 1.0),
        ("windsurf", 1.0),
        ("jet ski", 0.9),
        ("rafting", 0.9),
        ("kano", 0.8),
        ("tekne turu", 0.7),
        ("su sporu", 1.0),
        ("sualti", 0.9),
    ],
    "l2_hava_spor": [
        ("balon", 1.0),
        ("hot air balloon", 1.0),
        ("parasutu", 1.0),
        ("paragliding", 1.0),
        ("ucus", 0.7),
        ("gokyuzu", 0.7),
        ("skydiving", 1.0),
    ],
    "l2_doga_spor": [
        ("trekking", 1.0),
        ("hiking", 1.0),
        ("yuruyus", 0.9),
        ("dagcilik", 1.0),
        ("kamp", 0.9),
        ("bisiklet", 0.8),
        ("atv", 0.7),
        ("safari", 0.8),
        ("tirmanis", 0.9),
        ("patika", 0.7),
        ("kayak", 0.6),
    ],
    "l2_yemek": [
        ("yemek", 1.0),
        ("mutfak", 1.0),
        ("gastronomi", 1.0),
        ("lezzet", 0.9),
        ("restoran", 0.6),
        ("sokak lezzeti", 0.9),
        ("pazar", 0.5),
        ("deniz urunu", 0.8),
        ("kebap", 0.9),
        ("baklava", 0.9),
        ("sarap", 0.7),
        ("kahvalti", 0.6),
        ("cuisine", 0.8),
        ("food", 0.8),
    ],
    "l2_fotografik": [
        ("manzara", 1.0),
        ("fotograf", 1.0),
        ("ikonik", 0.8),
        ("panorama", 0.9),
        ("gun batimi", 0.9),
        ("renkli", 0.7),
        ("mimari", 0.7),
        ("dogal guzellik", 0.9),
        ("skyline", 0.8),
        ("view", 0.6),
        ("scenic", 0.8),
    ],
    "kis_spor": [
        ("kayak", 1.0),
        ("snowboard", 1.0),
        ("kar", 0.9),
        ("kis sporu", 1.0),
        ("pist", 0.9),
        ("teleferik", 0.7),
        ("buzul", 0.4),
        ("ski", 1.0),
    ],
}

REGION_PRIORS: dict[str, dict[str, float]] = {
    "Ege Kiyilari": {"l1_deniz": 0.82, "l1_sakin": 0.45, "l2_su_spor": 0.55},
    "Akdeniz Sahili": {"l1_deniz": 0.85, "l1_doga": 0.45, "l2_su_spor": 0.60},
    "Karadeniz": {"l1_doga": 0.85, "l1_sakin": 0.62, "l2_doga_spor": 0.55, "l2_fotografik": 0.65},
    "Tarihi Turkiye": {"l1_tarih": 0.88, "l2_kultur": 0.70, "l2_fotografik": 0.55},
    "Turkiye Sehirleri": {"l1_sehir_hayati": 0.72, "l2_kultur": 0.62, "l2_yemek": 0.58},
    "Balkanlar": {"l1_tarih": 0.65, "l2_kultur": 0.65, "l1_sakin": 0.45},
    "Kafkasya ve Ipek Yolu": {"l1_tarih": 0.70, "l2_kultur": 0.72, "l2_yemek": 0.50},
    "Kuzey Afrika": {"l1_tarih": 0.72, "l2_kultur": 0.72, "l2_fotografik": 0.66},
    "Japonya ve Guney Kore": {"l1_sehir_hayati": 0.75, "l2_kultur": 0.75, "l2_yemek": 0.62},
    "Singapur ve Malezya": {"l1_sehir_hayati": 0.75, "l2_yemek": 0.65, "l2_kultur": 0.58},
    "Latin Amerika Sehirleri": {"l1_sehir_hayati": 0.72, "l1_eglence": 0.68, "l2_kultur": 0.68},
    "Guney Amerika Doga": {"l1_doga": 0.92, "l1_macera": 0.82, "l2_fotografik": 0.82},
    "Guneydogu Asya": {"l1_deniz": 0.72, "l2_kultur": 0.62, "l2_yemek": 0.65, "l1_luks": 0.48},
    "Vietnam ve Hindistan": {"l2_kultur": 0.75, "l2_yemek": 0.62, "l1_tarih": 0.58},
    "Karayipler": {"l1_deniz": 0.92, "l1_sakin": 0.58, "l1_luks": 0.62},
    "Dogu Afrika": {"l1_doga": 0.88, "l1_macera": 0.78, "l2_fotografik": 0.75},
    "Orta Dogu Tarihi": {"l1_tarih": 0.88, "l2_kultur": 0.68, "l2_fotografik": 0.65},
    "Guney Asya Adalari": {"l1_doga": 0.68, "l1_deniz": 0.60, "l1_sakin": 0.58, "l2_kultur": 0.62},
    "Guney Avrupa": {"l1_tarih": 0.75, "l2_kultur": 0.78, "l2_yemek": 0.70},
    "Bati Avrupa": {"l1_sehir_hayati": 0.80, "l2_kultur": 0.82, "l1_tarih": 0.65},
    "Iskandinavya": {"l1_doga": 0.72, "l1_sakin": 0.62, "l1_sehir_hayati": 0.58},
    "Korfez": {"l1_luks": 0.88, "l1_sehir_hayati": 0.76, "l1_deniz": 0.42},
    "Kuzey Amerika": {"l1_sehir_hayati": 0.82, "l1_eglence": 0.70, "l2_kultur": 0.58},
    "Meksika ve Orta Amerika": {"l1_deniz": 0.58, "l2_kultur": 0.70, "l1_tarih": 0.58},
    "Okyanusya": {"l1_doga": 0.78, "l1_deniz": 0.68, "l1_macera": 0.65},
}

CITY_OVERRIDES: dict[str, dict[str, float]] = {
    "Bodrum": {"l1_deniz": 0.92, "l1_eglence": 0.90, "l1_luks": 0.82, "l1_sakin": 0.18},
    "Marmaris": {"l1_deniz": 0.90, "l1_eglence": 0.86, "l2_su_spor": 0.82},
    "Fethiye": {"l1_deniz": 0.86, "l1_doga": 0.78, "l1_macera": 0.88, "l2_hava_spor": 0.95},
    "Cesme": {"l1_deniz": 0.88, "l1_luks": 0.88, "l2_su_spor": 0.88, "l1_eglence": 0.76},
    "Datca": {"l1_deniz": 0.82, "l1_sakin": 0.92, "l1_luks": 0.30},
    "Kapadokya": {"l1_tarih": 0.86, "l2_hava_spor": 0.95, "l2_fotografik": 0.95, "l1_doga": 0.70},
    "Istanbul": {"l1_tarih": 0.95, "l2_kultur": 0.95, "l1_sehir_hayati": 0.95, "l2_yemek": 0.88},
    "Gaziantep": {"l2_yemek": 0.98, "l2_kultur": 0.72, "l1_luks": 0.25},
    "Maldivler": {"l1_deniz": 0.98, "l1_luks": 0.90, "l1_sakin": 0.82, "l2_su_spor": 0.88},
    "Dubai": {"l1_luks": 0.98, "l1_sehir_hayati": 0.92, "l1_eglence": 0.80},
    "Petra": {"l1_tarih": 0.98, "l2_fotografik": 0.92, "l1_doga": 0.55},
    "Luxor": {"l1_tarih": 0.98, "l2_kultur": 0.78, "l2_fotografik": 0.82},
    "Patagonia": {"l1_doga": 0.98, "l1_macera": 0.95, "l2_fotografik": 0.92, "l1_sakin": 0.78},
    "Queenstown": {"l1_doga": 0.92, "l1_macera": 0.95, "l2_doga_spor": 0.90},
    "Tromso": {"l1_doga": 0.86, "kis_spor": 0.75, "l2_fotografik": 0.86, "l1_sakin": 0.70},
    "New York": {"l1_sehir_hayati": 0.98, "l1_eglence": 0.90, "l2_kultur": 0.88, "l1_luks": 0.82},
    "Paris": {"l1_sehir_hayati": 0.90, "l2_kultur": 0.95, "l1_tarih": 0.82, "l1_luks": 0.82},
    "Tokyo": {"l1_sehir_hayati": 0.95, "l2_kultur": 0.88, "l2_yemek": 0.82, "l1_eglence": 0.78},
    "Kyoto": {"l1_tarih": 0.92, "l2_kultur": 0.95, "l1_sakin": 0.60},
    "Serengeti": {"l1_doga": 0.98, "l1_macera": 0.88, "l2_doga_spor": 0.72, "l2_fotografik": 0.90, "l1_sakin": 0.78, "l1_sehir_hayati": 0.08},
    # ── Faz D: sparse city enrichment ────────────────────────────────────────
    "Uzungol":       {"l1_doga": 0.88, "l1_sakin": 0.82, "l2_doga_spor": 0.65, "l2_yemek": 0.42},
    "Efes":          {"l1_tarih": 0.92, "l2_kultur": 0.78, "l1_sakin": 0.55, "l1_doga": 0.45},
    "Olu Deniz":     {"l1_deniz": 0.92, "l2_hava_spor": 0.90, "l1_doga": 0.75, "l1_sakin": 0.55, "l1_tarih": 0.10, "l2_kultur": 0.15},
    "Sanliurfa":     {"l1_tarih": 0.85, "l2_kultur": 0.72, "l2_yemek": 0.72, "l1_sakin": 0.48},
    "Marakes":       {"l1_tarih": 0.78, "l2_kultur": 0.82, "l2_yemek": 0.75, "l1_eglence": 0.55},
    "Fes":           {"l1_tarih": 0.85, "l2_kultur": 0.82, "l2_yemek": 0.68, "l1_sakin": 0.52},
    "Tunus":         {"l1_tarih": 0.72, "l2_kultur": 0.68, "l1_deniz": 0.58, "l2_yemek": 0.58},
    "Sidi Bou Said": {"l1_tarih": 0.72, "l2_kultur": 0.68, "l1_sakin": 0.82, "l1_deniz": 0.65},
    "Kairouan":      {"l1_tarih": 0.88, "l2_kultur": 0.72, "l1_sakin": 0.68},
    "Machu Picchu":  {"l1_doga": 0.82, "l1_tarih": 0.95, "l1_macera": 0.88, "l2_doga_spor": 0.85},
    "Amazon":        {"l1_doga": 0.98, "l1_sakin": 0.75, "l1_macera": 0.82, "l2_doga_spor": 0.82},
    "Galapagos":     {"l1_doga": 0.92, "l1_deniz": 0.78, "l1_sakin": 0.72},
    "Uyuni":         {"l1_doga": 0.92, "l1_sakin": 0.85, "l2_fotografik": 0.92, "l2_doga_spor": 0.62},
    "Zanzibar":      {"l1_deniz": 0.90, "l1_doga": 0.65, "l1_sakin": 0.72, "l1_tarih": 0.55},
    "Nairobi":       {"l1_doga": 0.58, "l2_kultur": 0.58, "l1_eglence": 0.48},
    "Kilimanjaro":   {"l1_doga": 0.95, "l1_macera": 0.95, "l2_doga_spor": 0.88, "l1_sakin": 0.80},
    "Kigali":        {"l1_doga": 0.62, "l2_kultur": 0.58, "l1_sakin": 0.62},
    "Wadi Rum":      {"l1_doga": 0.90, "l1_tarih": 0.55, "l1_sakin": 0.82, "l2_doga_spor": 0.75, "l2_kultur": 0.45},
    "Kahire":        {"l1_tarih": 0.95, "l2_kultur": 0.80, "l2_yemek": 0.58, "l1_eglence": 0.45},
    "Abu Dabi":      {"l1_luks": 0.88, "l1_sehir_hayati": 0.82, "l2_kultur": 0.68, "l1_tarih": 0.48, "l1_eglence": 0.55},
    "Doha":          {"l1_luks": 0.85, "l1_sehir_hayati": 0.78, "l2_kultur": 0.65, "l1_tarih": 0.45, "l1_eglence": 0.52},
    "Muskat":        {"l1_tarih": 0.72, "l1_deniz": 0.58, "l1_luks": 0.72, "l1_sehir_hayati": 0.55},
    "Riyad":         {"l1_tarih": 0.60, "l2_kultur": 0.52, "l1_luks": 0.82, "l1_sehir_hayati": 0.72},
    "Sydney":        {"l1_sehir_hayati": 0.88, "l1_eglence": 0.72, "l2_yemek": 0.62, "l1_deniz": 0.75},
    "Melbourne":     {"l1_sehir_hayati": 0.85, "l2_yemek": 0.80, "l1_eglence": 0.68, "l2_kultur": 0.62},
    "Suva":          {"l1_deniz": 0.72, "l1_doga": 0.65, "l1_sakin": 0.65},
}

PRICE_BY_REGION = {
    "Korfez": 0.90,
    "Bati Avrupa": 0.78,
    "Kuzey Amerika": 0.78,
    "Iskandinavya": 0.76,
    "Guney Avrupa": 0.68,
    "Okyanusya": 0.72,
    "Karayipler": 0.65,
    "Guneydogu Asya": 0.42,
    "Vietnam ve Hindistan": 0.32,
    "Balkanlar": 0.38,
    "Kafkasya ve Ipek Yolu": 0.35,
    "Kuzey Afrika": 0.35,
    "Turkiye Sehirleri": 0.48,
}

SEASON_WORDS = {
    0: ["yaz", "plaj", "sahil", "deniz", "gunes", "sicak", "summer"],
    1: ["kis", "kar", "kayak", "snowboard", "winter", "ski"],
    2: ["dort mevsim", "yil boyu", "her mevsim", "four season", "year round"],
}

FEATURE_LABELS = {
    "l1_deniz": "deniz",
    "l1_doga": "doga",
    "l1_tarih": "tarih",
    "l1_eglence": "eglence",
    "l1_sakin": "sakin",
    "l1_sehir_hayati": "sehir",
    "l1_macera": "macera",
    "l1_luks": "luks",
    "l2_kultur": "kultur",
    "l2_su_spor": "su_spor",
    "l2_hava_spor": "hava_spor",
    "l2_doga_spor": "doga_spor",
    "l2_yemek": "yemek",
    "l2_fotografik": "fotografik",
    "kis_spor": "kis_spor",
}

SUMMARY_PHRASES = {
    "l1_deniz": "kiyi ve su deneyimi",
    "l1_doga": "dogal manzara",
    "l1_tarih": "tarihi doku",
    "l1_eglence": "canli sosyal tempo",
    "l1_sakin": "sakin kacis",
    "l1_sehir_hayati": "kent enerjisi",
    "l1_macera": "macera",
    "l1_luks": "konfor",
    "l2_kultur": "kulturel kesif",
    "l2_su_spor": "su sporlari",
    "l2_hava_spor": "havadan deneyimler",
    "l2_doga_spor": "aktif doga",
    "l2_yemek": "yerel lezzetler",
    "l2_fotografik": "fotografik sahneler",
    "kis_spor": "kis sporlari",
}

SUMMARY_OPENERS = [
    "{environment}; {a}, {b} ve {c} dengesini arayanlar icin {pace} bir rota sunar.",
    "{environment}; {a} odagi guclu, {b} ve {c} tarafiyla desteklenen {pace} bir deneyim verir.",
    "{environment}; {a} isteyen, ayni zamanda {b} ve {c} bekleyen gezginlere {pace} bir alternatif olur.",
    "{environment}; {a} hissini {b} ve {c} ile birlestiren {pace} bir seyahat secenegidir.",
]

TITLE_PATTERNS = [
    "{a} + {b}",
    "{a}, {b} odakli",
    "{a} ve {c}",
    "{b} ile {a}",
]


def ascii_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    translated = value.translate(CHAR_MAP)
    normalized = unicodedata.normalize("NFKD", translated)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.split())


def slug(value: str) -> str:
    value = ascii_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def read_catalog() -> list[dict[str, str]]:
    with CATALOG_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_catalog(rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with CATALOG_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_texts() -> dict[str, str]:
    raw = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
    return {ascii_text(k): v for k, v in raw.items()}


def load_descriptions() -> dict[str, dict[str, str]]:
    if not DESCRIPTION_PATH.exists():
        return {}
    raw = json.loads(DESCRIPTION_PATH.read_text(encoding="utf-8"))
    return {ascii_text(k): v for k, v in raw.items()}


def build_text_sources(
    catalog_rows: list[dict[str, str]],
    texts: dict[str, str],
    descriptions: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    sources = {}
    for row in catalog_rows:
        city = row["sehir"]
        desc = descriptions.get(city, {})
        source_parts = [
            desc.get("TR", ""),
            desc.get("EN", ""),
            texts.get(city, ""),
        ]
        source_text = ascii_text("\n".join(part.strip() for part in source_parts if part.strip()))
        sources[city] = {
            "city": city,
            "region": row["bolge_adi"],
            "country": row["ulke"],
            "source_text": source_text,
            "has_curated_description": bool(desc),
        }
    TEXT_SOURCE_PATH.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return sources


def normalize_for_match(text: str) -> str:
    text = ascii_text(text).lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def term_count(text: str, term: str) -> int:
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return len(re.findall(pattern, text))


def keyword_score(text: str, feature: str) -> float:
    weighted = 0.0
    hits = 0
    for term, weight in KEYWORDS[feature]:
        count = term_count(text, normalize_for_match(term))
        if count:
            hits += count
            weighted += min(count, 4) * weight
    if weighted <= 0:
        return 0.08
    # Smooth saturation: 3 weighted hits is visible, 8+ is dominant.
    score = 1.0 - math.exp(-weighted / 4.2)
    if hits >= 5:
        score += 0.08
    return clamp(score)


def clamp(value: float, lo: float = 0.0, hi: float = 0.98) -> float:
    return max(lo, min(hi, value))


def blend(base: float, prior: float, prior_weight: float = 0.62) -> float:
    return clamp(base * (1.0 - prior_weight) + prior * prior_weight)


def compute_scores(row: dict[str, str], text: str) -> dict[str, float]:
    clean = normalize_for_match(text)
    scores = {feature: keyword_score(clean, feature) for feature in SCORE_COLUMNS}

    for feature, prior in REGION_PRIORS.get(row["bolge_adi"], {}).items():
        scores[feature] = blend(scores[feature], prior)

    # Expensive destination score: explicit luxury keywords + region price prior.
    price_prior = PRICE_BY_REGION.get(row["bolge_adi"], 0.50)
    scores["l1_luks"] = blend(scores["l1_luks"], price_prior, 0.30)

    # City life and calm should not both dominate unless text strongly supports both.
    if scores["l1_sehir_hayati"] > 0.75 and scores["l1_sakin"] > 0.65:
        scores["l1_sakin"] = min(scores["l1_sakin"], 0.58)
    if scores["l1_sakin"] > 0.78 and scores["l1_sehir_hayati"] > 0.60:
        scores["l1_sehir_hayati"] = min(scores["l1_sehir_hayati"], 0.55)

    if scores["kis_spor"] > 0.55:
        scores["l1_macera"] = max(scores["l1_macera"], scores["kis_spor"] * 0.75)
        scores["l1_doga"] = max(scores["l1_doga"], 0.45)

    if scores["l2_su_spor"] > 0.60:
        scores["l1_deniz"] = max(scores["l1_deniz"], 0.55)
        scores["l1_macera"] = max(scores["l1_macera"], scores["l2_su_spor"] * 0.55)

    if scores["l2_hava_spor"] > 0.60:
        scores["l1_macera"] = max(scores["l1_macera"], scores["l2_hava_spor"] * 0.70)
        scores["l2_fotografik"] = max(scores["l2_fotografik"], 0.70)

    if row["sehir"] in CITY_OVERRIDES:
        scores.update(CITY_OVERRIDES[row["sehir"]])

    return {key: round(clamp(value), 3) for key, value in scores.items()}


def price_label(score: float) -> str:
    if score < 0.30:
        return "dusuk"
    if score < 0.55:
        return "orta"
    if score < 0.78:
        return "yuksek"
    return "luks"


def season_value(scores: dict[str, float], text: str) -> tuple[int, str]:
    clean = normalize_for_match(text)
    season_hits = {
        season: sum(term_count(clean, normalize_for_match(term)) for term in terms)
        for season, terms in SEASON_WORDS.items()
    }
    if scores["kis_spor"] >= 0.62:
        return 1, "kis"
    if season_hits[2] > 0:
        return 2, "dort_mevsim"
    if scores["l1_deniz"] >= 0.70 and scores["kis_spor"] < 0.35:
        return 0, "yaz"
    if scores["l1_tarih"] >= 0.70 or scores["l1_sehir_hayati"] >= 0.70:
        return 2, "dort_mevsim"
    if season_hits[1] > season_hits[0]:
        return 1, "kis"
    if season_hits[0] > 0:
        return 0, "yaz"
    return 2, "dort_mevsim"


def to_model_row(row: dict[str, Any], scores: dict[str, float], mevsim: int) -> dict[str, Any]:
    model = {
        "id": row["sehir"],
        "sehir": row["sehir"],
        "region_id": f"region_{int(row['bolge_id']):02d}_{slug(row['bolge_adi'])}",
        "country": row["ulke"],
        "visa_free": row["tr_vize"] != "vizeli",
        "deniz": scores["l1_deniz"],
        "doga": scores["l1_doga"],
        "tarih": scores["l1_tarih"],
        "kultur": scores["l2_kultur"],
        "doga_spor": round(clamp(scores["l2_doga_spor"] * 0.72 + scores["l1_macera"] * 0.28), 3),
        "su_spor": scores["l2_su_spor"],
        "hava_spor": scores["l2_hava_spor"],
        "kis_spor": scores["kis_spor"],
        "eglence": scores["l1_eglence"],
        "sakin": scores["l1_sakin"],
        "yemek": scores["l2_yemek"],
        "ulasim_kolayligi": round(clamp(scores["l1_sehir_hayati"] * 0.78 + 0.18), 3),
        "fiyat": scores["l1_luks"],
        "mevsim": mevsim,
    }
    return model


def top_features(scores: dict[str, float], n: int = 4) -> list[str]:
    useful = {key: value for key, value in scores.items() if value >= 0.45}
    ordered = sorted(useful, key=lambda key: useful[key], reverse=True)
    if len(ordered) >= n:
        return ordered[:n]
    fallback = [key for key in sorted(scores, key=scores.get, reverse=True) if key not in ordered]
    return (ordered + fallback)[:n]


def meaningful_features(scores: dict[str, float], n: int = 5, threshold: float = 0.40) -> list[str]:
    ordered = [key for key in sorted(scores, key=scores.get, reverse=True) if scores[key] >= threshold]
    return ordered[:n]


def display_features(scores: dict[str, float], n: int = 4) -> list[str]:
    meaningful = meaningful_features(scores, n)
    if len(meaningful) >= min(2, n):
        return meaningful
    return top_features(scores, n)


def hidden_title(city: str, scores: dict[str, float]) -> str:
    top = display_features(scores, 3)
    labels = [SUMMARY_PHRASES[key] for key in top]
    if len(labels) == 1:
        return labels[0].capitalize()
    values = {"a": labels[0], "b": labels[1], "c": labels[2] if len(labels) > 2 else labels[0]}
    pattern = TITLE_PATTERNS[stable_index(city, len(TITLE_PATTERNS))]
    return pattern.format(**values).capitalize()


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 25]


def stable_index(value: str, modulo: int) -> int:
    return sum(ord(ch) for ch in value) % modulo


def sanitize_sentence(sentence: str, row: dict[str, Any]) -> str:
    cleaned = ascii_text(sentence)
    blocked = {
        row["sehir"],
        row["ulke"],
        row["bolge_adi"],
        "Turkey",
        "Turkiye",
    }
    for value in blocked:
        if value:
            cleaned = re.sub(rf"\b{re.escape(ascii_text(value))}\b", "bu rota", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b", "ikonik noktalar", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned


def evidence_sentence(row: dict[str, Any], source_text: str, features: list[str]) -> str:
    clean_features = set(features)
    best = ""
    best_score = -1.0
    for sentence in split_sentences(source_text):
        normalized = normalize_for_match(sentence)
        score = 0.0
        for feature in clean_features:
            for term, weight in KEYWORDS.get(feature, []):
                if term_count(normalized, normalize_for_match(term)):
                    score += weight
        score += min(len(sentence), 220) / 900.0
        if score > best_score:
            best_score = score
            best = sentence
    return sanitize_sentence(best, row) if best else ""


def source_hint_terms(
    source_text: str,
    features: list[str],
    blocked_terms: set[str],
    limit: int = 4,
) -> list[str]:
    normalized = normalize_for_match(source_text)
    found = []
    for feature in features:
        for term, _ in KEYWORDS.get(feature, []):
            term_norm = normalize_for_match(term)
            if not term_norm or term_norm in blocked_terms:
                continue
            if term_norm and term_count(normalized, term_norm) and term_norm not in found:
                found.append(term_norm)
                break
        if len(found) >= limit:
            break
    return found


def hidden_summary(row: dict[str, Any], scores: dict[str, float], source_text: str) -> str:
    top = display_features(scores, 4)
    labels = [SUMMARY_PHRASES[key] for key in top]
    while len(labels) < 4:
        labels.append("dengeli tempo")

    if scores["l1_deniz"] >= 0.78:
        environment = "Kiyi atmosferi"
    elif scores["l1_doga"] >= 0.78:
        environment = "Doga odakli bir rota"
    elif scores["l1_sehir_hayati"] >= 0.75:
        environment = "Kent enerjisi yuksek bir durak"
    elif scores["l1_tarih"] >= 0.75:
        environment = "Tarihi dokuya yaslanan bir rota"
    else:
        environment = "Dengeli ve karakterli bir durak"

    pace = "sakin tempolu" if scores["l1_sakin"] >= 0.70 else "hareketli" if scores["l1_eglence"] >= 0.70 else "orta tempolu"
    values = {
        "environment": environment,
        "a": labels[0],
        "b": labels[1],
        "c": labels[2],
        "d": labels[3],
        "pace": pace,
    }
    base = SUMMARY_OPENERS[stable_index(row["sehir"], len(SUMMARY_OPENERS))].format(**values)
    blocked_terms = {
        normalize_for_match(row["sehir"]),
        normalize_for_match(row["ulke"]),
        normalize_for_match(row["bolge_adi"]),
    }
    hints = source_hint_terms(source_text, top, blocked_terms)
    if hints:
        return f"{base} Metin sinyalleri: {', '.join(hints)}."
    return base


def reveal_summary(row: dict[str, Any], scores: dict[str, float], source_text: str) -> str:
    tags = [SUMMARY_PHRASES[key] for key in display_features(scores, 3)]
    evidence = evidence_sentence(row, source_text, display_features(scores, 3))
    if evidence:
        evidence = evidence[:150].rstrip()
        return f"{row['sehir']}: {evidence}. One cikan eksenler: {', '.join(tags)}."
    return f"{row['sehir']}: {', '.join(tags)} ozellikleriyle one cikan bir destinasyondur."


def make_region_hidden_description(region_name: str, rows: list[dict[str, Any]]) -> str:
    avg = {
        key: sum(float(row[key]) for row in rows) / len(rows)
        for key in SCORE_COLUMNS
    }
    top = [SUMMARY_PHRASES[key] for key in top_features(avg, 3)]
    return (
        f"{top[0].title()}, {top[1]} ve {top[2]} ekseninde sekillenen; "
        "isimlerden bagimsiz olarak deneyim hissiyle secilecek bir rota."
    )


def make_open_region_description(region_name: str, rows: list[dict[str, Any]]) -> str:
    countries = sorted({row["ulke"] for row in rows})
    return (
        f"{region_name}; {', '.join(countries[:4])} odakli, "
        f"{len(rows)} destinasyondan olusan seyahat bolgesidir."
    )


def write_model_csv(model_rows: list[dict[str, Any]]) -> None:
    columns = [
        "id",
        "sehir",
        "region_id",
        "country",
        "visa_free",
        *PHYSICAL,
        *SOCIOLOGICAL,
        "mevsim",
    ]
    with MODEL_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(model_rows)


def write_cities_json(
    catalog_rows: list[dict[str, Any]],
    model_by_city: dict[str, dict[str, Any]],
    score_by_city: dict[str, dict[str, float]],
    text_sources: dict[str, dict[str, Any]],
) -> None:
    cities = []
    hidden_summaries = {}
    for row in catalog_rows:
        city = row["sehir"]
        model = model_by_city[city]
        scores = score_by_city[city]
        source_text = text_sources[city]["source_text"]
        h_title = hidden_title(city, scores)
        h_summary = hidden_summary(row, scores, source_text)
        tags = [FEATURE_LABELS[key] for key in meaningful_features(scores, 5)]
        r_summary = reveal_summary(row, scores, source_text)
        cities.append(
            {
                "id": city,
                "name": city,
                "route_id": model["region_id"],
                "country": model["country"],
                "visa_free": model["visa_free"],
                "visa": {"TR": row["tr_vize"], "US": row["us_vize"]},
                "physical_vector": {key: model[key] for key in PHYSICAL},
                "sociological_vector": {key: model[key] for key in SOCIOLOGICAL},
                "catalog_scores": {key: scores[key] for key in SCORE_COLUMNS},
                "mevsim": model["mevsim"],
                "hidden_title": h_title,
                "hidden_summary": h_summary,
                "hidden_tags": tags,
                "reveal_summary": r_summary,
                "text_source": "destination_text_sources.json",
                "nlp_confidence": confidence_score(scores),
            }
        )
        hidden_summaries[city] = {
            "hidden_title": h_title,
            "hidden_summary": h_summary,
            "hidden_tags": tags,
            "reveal_summary": r_summary,
            "text_source": "destination_text_sources.json",
        }
    CITIES_PATH.write_text(json.dumps(cities, ensure_ascii=False, indent=2), encoding="utf-8")
    HIDDEN_SUMMARIES_PATH.write_text(
        json.dumps(hidden_summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def confidence_score(scores: dict[str, float]) -> float:
    strong = sum(1 for value in scores.values() if value >= 0.60)
    spread = max(scores.values()) - min(scores.values())
    return round(clamp(0.58 + strong * 0.035 + spread * 0.18, 0.55, 0.92), 3)


def write_regions_json(catalog_rows: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in catalog_rows:
        grouped[row["bolge_id"]].append(row)

    regions = []
    for bolge_id in sorted(grouped, key=lambda x: int(x)):
        rows = grouped[bolge_id]
        name = rows[0]["bolge_adi"]
        region_id = f"region_{int(bolge_id):02d}_{slug(name)}"
        countries = sorted({row["ulke"] for row in rows})
        visa_free = any(row["tr_vize"] != "vizeli" for row in rows)
        season_counts = Counter(row["en_iyi_mevsim"] for row in rows)
        regions.append(
            {
                "id": region_id,
                "name": name,
                "country_scope": countries,
                "visa_free": visa_free,
                "sub_destinations": [row["sehir"] for row in rows],
                "hidden_description": make_region_hidden_description(name, rows),
                "open_description": make_open_region_description(name, rows),
                "season_score": season_profile(season_counts),
                "is_winter_only": season_counts.get("kis", 0) >= max(2, len(rows) // 2),
                "duration_days": {"min": 3, "ideal": 7, "max": 14},
            }
        )
    REGIONS_PATH.write_text(json.dumps(regions, ensure_ascii=False, indent=2), encoding="utf-8")


def season_profile(counts: Counter[str]) -> dict[str, float]:
    total = max(sum(counts.values()), 1)
    return {
        "summer": round((counts.get("yaz", 0) + counts.get("dort_mevsim", 0) * 0.7) / total, 3),
        "spring": round((counts.get("dort_mevsim", 0) + counts.get("yaz", 0) * 0.5) / total, 3),
        "autumn": round((counts.get("dort_mevsim", 0) + counts.get("kis", 0) * 0.3) / total, 3),
        "winter": round((counts.get("kis", 0) + counts.get("dort_mevsim", 0) * 0.5) / total, 3),
    }


def write_report(
    catalog_rows: list[dict[str, Any]],
    score_by_city: dict[str, dict[str, float]],
    model_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Vector Quality Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Destinations: {len(catalog_rows)}",
        f"Regions: {len({row['bolge_id'] for row in catalog_rows})}",
        "",
        "## Score Columns",
        "",
        "| column | min | mean | max | high_count |",
        "|---|---:|---:|---:|---:|",
    ]
    for column in SCORE_COLUMNS:
        values = [score_by_city[row["sehir"]][column] for row in catalog_rows]
        high_count = sum(value >= 0.70 for value in values)
        lines.append(
            f"| {column} | {min(values):.3f} | {sum(values)/len(values):.3f} | "
            f"{max(values):.3f} | {high_count} |"
        )

    lines.extend(["", "## Top Feature Samples", ""])
    for row in catalog_rows[:]:
        city = row["sehir"]
        scores = score_by_city[city]
        top = ", ".join(f"{FEATURE_LABELS[key]}={scores[key]:.2f}" for key in top_features(scores, 4))
        lines.append(f"- **{city}**: {top}")

    suspicious = []
    for model in model_rows:
        if model["deniz"] > 0.65 and model["country"] not in {"Turkiye"} and model["region_id"].endswith("guney_amerika_doga"):
            suspicious.append(f"{model['sehir']}: high deniz in inland nature region")
        if model["kis_spor"] > 0.50 and model["mevsim"] != 1:
            suspicious.append(f"{model['sehir']}: winter score high but season not winter")
        meaningful = sum(float(model[key]) >= 0.40 for key in PHYSICAL + SOCIOLOGICAL)
        if meaningful < 3:
            suspicious.append(f"{model['sehir']}: fewer than 3 meaningful model features")

    lines.extend(["", "## Checks", ""])
    if suspicious:
        lines.extend(f"- {item}" for item in suspicious)
    else:
        lines.append("- No automatic quality warnings.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_ascii_outputs() -> None:
    for path in [
        CATALOG_PATH,
        MODEL_PATH,
        CITIES_PATH,
        HIDDEN_SUMMARIES_PATH,
        REGIONS_PATH,
        REPORT_PATH,
        TEXT_SOURCE_PATH,
    ]:
        text = path.read_text(encoding="utf-8")
        try:
            text.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(f"Non-ASCII output in {path}: {exc}") from exc


def main() -> None:
    catalog_rows = read_catalog()
    texts = load_texts()
    descriptions = load_descriptions()
    text_sources = build_text_sources(catalog_rows, texts, descriptions)
    fieldnames = list(catalog_rows[0].keys())

    score_by_city: dict[str, dict[str, float]] = {}
    model_rows: list[dict[str, Any]] = []
    model_by_city: dict[str, dict[str, Any]] = {}

    for row in catalog_rows:
        city = row["sehir"]
        if city not in texts:
            raise ValueError(f"Missing text for {city}")

        source_text = text_sources[city]["source_text"]
        scores = compute_scores(row, source_text)
        mevsim, season_label = season_value(scores, source_text)
        score_by_city[city] = scores

        for column in SCORE_COLUMNS:
            row[column] = f"{scores[column]:.3f}"
        row["fiyat_seviye"] = price_label(scores["l1_luks"])
        row["en_iyi_mevsim"] = season_label

        model = to_model_row(row, scores, mevsim)
        model_rows.append(model)
        model_by_city[city] = model

    write_catalog(catalog_rows, fieldnames)
    write_model_csv(model_rows)
    write_cities_json(catalog_rows, model_by_city, score_by_city, text_sources)
    write_regions_json(catalog_rows)
    write_report(catalog_rows, score_by_city, model_rows)
    validate_ascii_outputs()

    print(f"Wrote scores for {len(catalog_rows)} destinations.")
    print(f"Wrote model vectors: {MODEL_PATH}")
    print(f"Wrote city summaries: {CITIES_PATH}")
    print(f"Wrote hidden summaries: {HIDDEN_SUMMARIES_PATH}")
    print(f"Wrote text sources: {TEXT_SOURCE_PATH}")
    print(f"Wrote regions: {REGIONS_PATH}")
    print(f"Wrote quality report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
