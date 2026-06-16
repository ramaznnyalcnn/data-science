"""
Wikipedia Scraper
Her destinasyon için Wikipedia'dan özet metin çeker ve sehir_metinleri.json'a kaydeder.
Kullanım: python scripts/wiki_scraper.py [--limit N] [--bolge_id N] [--lang tr|en]
"""

import requests
import pandas as pd
import json
import time
import argparse
from pathlib import Path

CSV_PATH   = Path(__file__).parent.parent / "data" / "destinasyonlar.csv"
JSON_PATH  = Path(__file__).parent.parent / "data" / "sehir_metinleri.json"

# Wikipedia arama başlıkları için özel eşlemeler
WIKI_MAP = {
    # Türkiye
    "Kapadokya":        {"tr": "Kapadokya",         "en": "Cappadocia"},
    "Efes":             {"tr": "Efes",               "en": "Ephesus"},
    "Şanlıurfa":        {"tr": "Şanlıurfa",          "en": "Şanlıurfa"},
    "Uzungöl":          {"tr": "Uzungöl",            "en": "Uzungöl"},
    "Ayder":            {"tr": "Ayder Yaylası",      "en": "Ayder Plateau"},
    # Balkanlar
    "Tiran":            {"tr": "Tiran",              "en": "Tirana"},
    "Beograd":          {"tr": "Belgrad",            "en": "Belgrade"},
    "Kotor":            {"tr": "Kotor",              "en": "Kotor, Montenegro"},
    "Mostar":           {"tr": "Mostar",             "en": "Mostar"},
    "Üsküp":            {"tr": "Üsküp",              "en": "Skopje"},
    # Kafkasya
    "Bakü":             {"tr": "Bakü",               "en": "Baku"},
    "Tiflis":           {"tr": "Tiflis",             "en": "Tbilisi"},
    "Semerkant":        {"tr": "Semerkant",          "en": "Samarkand"},
    "Buhara":           {"tr": "Buhara",             "en": "Bukhara"},
    "Taşkent":          {"tr": "Taşkent",            "en": "Tashkent"},
    # Kuzey Afrika
    "Marakeş":          {"tr": "Marakeş",            "en": "Marrakesh"},
    "Sidi Bou Said":    {"tr": "Sidi Bou Said",      "en": "Sidi Bou Said"},
    "Kairouan":         {"tr": "Kayrevan",           "en": "Kairouan"},
    # Japonya / Kore
    "Seoul":            {"tr": "Seul",               "en": "Seoul"},
    # Güneydoğu Asya
    "Siem Reap":        {"tr": "Siem Reap",          "en": "Siem Reap"},
    "Krabi":            {"tr": "Krabi",              "en": "Krabi Province"},
    # Latin Amerika
    "Rio de Janeiro":   {"tr": "Rio de Janeiro",     "en": "Rio de Janeiro"},
    "Buenos Aires":     {"tr": "Buenos Aires",       "en": "Buenos Aires"},
    "Santiago":         {"tr": "Santiago, Şili",     "en": "Santiago"},
    "Bogota":           {"tr": "Bogota",             "en": "Bogotá"},
    # Güney Amerika Doğa
    "Patagonia":        {"tr": "Patagonya",          "en": "Patagonia"},
    "Machu Picchu":     {"tr": "Machu Picchu",       "en": "Machu Picchu"},
    "Amazon":           {"tr": "Amazon ormanı",      "en": "Amazon rainforest"},
    "Galapagos":        {"tr": "Galapagos Adaları",  "en": "Galápagos Islands"},
    "Uyuni":            {"tr": "Uyuni Tuz Çölü",     "en": "Salar de Uyuni"},
    # Karayipler
    "Punta Cana":       {"tr": "Punta Cana",         "en": "Punta Cana"},
    "Havana":           {"tr": "Havana",             "en": "Havana"},
    "Nassau":           {"tr": "Nassau, Bahamalar",  "en": "Nassau, Bahamas"},
    "Montego Bay":      {"tr": "Montego Bay",        "en": "Montego Bay"},
    # Doğu Afrika
    "Zanzibar":         {"tr": "Zanzibar",           "en": "Zanzibar"},
    "Serengeti":        {"tr": "Serengeti",          "en": "Serengeti National Park"},
    "Kilimanjaro":      {"tr": "Kilimanjaro",        "en": "Mount Kilimanjaro"},
    "Kigali":           {"tr": "Kigali",             "en": "Kigali"},
    # Orta Doğu
    "Petra":            {"tr": "Petra",              "en": "Petra, Jordan"},
    "Wadi Rum":         {"tr": "Vadi Ram",           "en": "Wadi Rum"},
    "Ölü Deniz":        {"tr": "Ölü Deniz",          "en": "Dead Sea"},
    "Luxor":            {"tr": "Lüksor",             "en": "Luxor"},
    # Güney Asya
    "Maldivler":        {"tr": "Maldivler",          "en": "Maldives"},
    "Colombo":          {"tr": "Kolombo",            "en": "Colombo"},
    "Galle":            {"tr": "Galle",              "en": "Galle, Sri Lanka"},
    # Avrupa
    "Barselona":        {"tr": "Barselona",          "en": "Barcelona"},
    "Atina":            {"tr": "Atina",              "en": "Athens"},
    "Stockholm":        {"tr": "Stockholm",          "en": "Stockholm"},
    "Tromsø":           {"tr": "Tromsø",             "en": "Tromsø"},
    "Muskat":           {"tr": "Maskat",             "en": "Muscat, Oman"},
    "Zanzibar":         {"tr": "Zanzibar",           "en": "Zanzibar Archipelago"},
    "Kilimanjaro":      {"tr": "Kilimanjaro",        "en": "Mount Kilimanjaro"},
    "Wadi Rum":         {"tr": "Vadi Ram",           "en": "Wadi Rum"},
    "Ölü Deniz":        {"tr": "Ölü Deniz",          "en": "Dead Sea"},
    "Kahire":           {"tr": "Kahire",             "en": "Cairo"},
    "Nassau":           {"tr": "Nassau",             "en": "Nassau, Bahamas"},
    "Montego Bay":      {"tr": "Montego Bay",        "en": "Montego Bay"},
    "Jaipur":           {"tr": "Jaipur",             "en": "Jaipur"},
    "Varanasi":         {"tr": "Varanasi",           "en": "Varanasi"},
    "Queenstown":       {"tr": "Queenstown",         "en": "Queenstown, New Zealand"},
    "Krabi":            {"tr": "Krabi",              "en": "Krabi Province"},
    "Siem Reap":        {"tr": "Siem Reap",          "en": "Siem Reap"},
    "Santorini":        {"tr": "Santorini",          "en": "Santorini"},
    "Floransa":         {"tr": "Floransa",           "en": "Florence"},
    "Amsterdam":        {"tr": "Amsterdam",          "en": "Amsterdam"},
    "Londra":           {"tr": "Londra",             "en": "London"},
    "Brüksel":          {"tr": "Brüksel",            "en": "Brussels"},
    "Dublin":           {"tr": "Dublin",             "en": "Dublin"},
    "Viyana":           {"tr": "Viyana",             "en": "Vienna"},
    "Kopenhag":         {"tr": "Kopenhag",           "en": "Copenhagen"},
    "Stockholm":        {"tr": "Stockholm",          "en": "Stockholm"},
    "Helsinki":         {"tr": "Helsinki",           "en": "Helsinki"},
    "Tromsø":           {"tr": "Tromsø",             "en": "Tromsø"},
    # Körfez
    "Dubai":            {"tr": "Dubai",              "en": "Dubai"},
    "Abu Dabi":         {"tr": "Abu Dabi",           "en": "Abu Dhabi"},
    "Doha":             {"tr": "Doha",               "en": "Doha"},
    "Muskat":           {"tr": "Maskat",             "en": "Muscat, Oman"},
    "Riyad":            {"tr": "Riyad",              "en": "Riyadh"},
    # Kuzey Amerika
    "New York":         {"tr": "New York",           "en": "New York City"},
    "Los Angeles":      {"tr": "Los Angeles",        "en": "Los Angeles"},
    "San Francisco":    {"tr": "San Francisco",      "en": "San Francisco"},
    "Toronto":          {"tr": "Toronto",            "en": "Toronto"},
    # Meksika / Orta Amerika
    "Cancun":           {"tr": "Cancún",             "en": "Cancún"},
    "Meksiko":          {"tr": "Meksiko City",       "en": "Mexico City"},
    "San Jose":         {"tr": "San José",           "en": "San José, Costa Rica"},
    "Cartagena":        {"tr": "Cartagena",          "en": "Cartagena, Colombia"},
    "Panama City":      {"tr": "Panama City",        "en": "Panama City"},
    "Cartagena":        {"tr": "Cartagena, Kolombiya","en": "Cartagena, Colombia"},
    # Okyanusya
    "Queenstown":       {"tr": "Queenstown, Yeni Zelanda","en": "Queenstown, New Zealand"},
    "Suva":             {"tr": "Suva",               "en": "Suva"},
    "Papeete":          {"tr": "Papeete",            "en": "Papeete"},
    # Singapur / Malezya
    "Uzungöl":          {"tr": "Uzungöl",            "en": "Uzungöl"},
    "Artvin":           {"tr": "Artvin",             "en": "Artvin Province"},
    "Buhara":           {"tr": "Buhara",             "en": "Bukhara"},
    "Singapur":         {"tr": "Singapur",           "en": "Singapore"},
    "Kuala Lumpur":     {"tr": "Kuala Lumpur",       "en": "Kuala Lumpur"},
    "Hong Kong":        {"tr": "Hong Kong",          "en": "Hong Kong"},
    "Macau":            {"tr": "Makao",              "en": "Macau"},
    # Vietnam / Hindistan
    "Ho Chi Minh":      {"tr": "Ho Chi Minh",        "en": "Ho Chi Minh City"},
    "Goa":              {"tr": "Goa",                "en": "Goa"},
    "Jaipur":           {"tr": "Jaipur",             "en": "Jaipur"},
    "Varanasi":         {"tr": "Varanasi",           "en": "Varanasi"},
}

HEADERS = {"User-Agent": "DataScienceProject/1.0 (educational; contact: student)"}


def wiki_summary(title: str, lang: str = "en") -> str | None:
    """Wikipedia REST API ile özet metin çeker."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("extract", "")
        return None
    except Exception:
        return None


def wiki_sections(title: str, lang: str = "en") -> str | None:
    """Wikipedia API ile turizm/coğrafya bölümlerini çeker."""
    url = "https://{lang}.wikipedia.org/w/api.php".format(lang=lang)
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exsectionformat": "plain",
        "explaintext": True,
        "exlimit": 1,
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract:
                    # İlk 3000 karakter yeterli
                    return extract[:3000]
        return None
    except Exception:
        return None


def fetch_destination(sehir: str, lang_pref: str = "en") -> str:
    """Bir şehir için en iyi Wikipedia metnini döndürür."""
    mapping = WIKI_MAP.get(sehir, {})

    # Önce tam metin dene, sonra özet
    for lang in ([lang_pref, "en"] if lang_pref != "en" else ["en", "tr"]):
        title = mapping.get(lang, sehir)

        # Önce tam bölümleri dene
        text = wiki_sections(title, lang)
        if text and len(text) > 100:
            return text.strip()

        # Sonra özet
        text = wiki_summary(title, lang)
        if text and len(text) > 50:
            return text.strip()

    # Son çare: Wikipedia arama API'si ile en iyi eşleşmeyi bul
    text = wiki_search_fallback(sehir)
    return text.strip() if text else ""


def wiki_search_fallback(query: str) -> str | None:
    """Wikipedia arama API'si ile en iyi sonucu çeker."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            results = r.json().get("query", {}).get("search", [])
            if results:
                top_title = results[0]["title"]
                text = wiki_sections(top_title, "en")
                if text and len(text) > 100:
                    return text
                text = wiki_summary(top_title, "en")
                if text and len(text) > 50:
                    return text
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Wikipedia Destination Scraper")
    parser.add_argument("--limit",    type=int, default=None, help="Kaç şehir işlensin")
    parser.add_argument("--bolge_id", type=int, default=None, help="Sadece bu bölge")
    parser.add_argument("--force",    action="store_true",    help="Mevcut verileri de yenile")
    parser.add_argument("--lang",     default="en", choices=["en","tr"], help="Tercih dil")
    args = parser.parse_args()

    df = pd.read_csv(CSV_PATH)

    # Mevcut metinleri yükle
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            metinler = json.load(f)
    else:
        metinler = {}

    # Hedef şehirleri belirle
    targets = df.copy()
    if args.bolge_id:
        targets = targets[targets["bolge_id"] == args.bolge_id]
    if not args.force:
        targets = targets[~targets["sehir"].isin(metinler.keys())]
    if args.limit:
        targets = targets.head(args.limit)

    total = len(targets)
    print(f"\n{'='*55}")
    print(f"Mevcut: {len(metinler)} şehir | Eklenecek: {total} şehir")
    print(f"{'='*55}\n")

    if total == 0:
        print("Tüm şehirler zaten mevcut. --force ile yenileyebilirsin.")
        return

    for i, (_, row) in enumerate(targets.iterrows(), 1):
        sehir = row["sehir"]
        print(f"[{i:3}/{total}] {sehir}, {row['ulke']}... ", end="", flush=True)

        text = fetch_destination(sehir, args.lang)

        if text:
            metinler[sehir] = text
            with open(JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(metinler, f, ensure_ascii=False, indent=2)
            print(f"✓ ({len(text)} karakter)")
        else:
            print("✗ bulunamadı")

        time.sleep(0.3)  # Wikipedia rate limit

    print(f"\n{'='*55}")
    print(f"Tamamlandı. Toplam: {len(metinler)}/125 şehir")
    print(f"JSON: {JSON_PATH}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
