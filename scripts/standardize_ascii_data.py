"""Standardize data identifiers to ASCII.

This script normalizes identifiers and catalog fields such as city, country,
region names, JSON keys, and training labels. Free-text descriptions are left
unchanged so the NLP scorer can still benefit from Turkish text.
"""

from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CHAR_MAP = str.maketrans(
    {
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "I": "I",
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


def ascii_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    translated = value.translate(CHAR_MAP)
    normalized = unicodedata.normalize("NFKD", translated)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.split())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def standardize_destination_catalog() -> tuple[set[str], dict[str, str]]:
    path = DATA / "destinasyonlar.csv"
    rows = read_csv(path)
    if not rows:
        return set(), {}

    name_map: dict[str, str] = {}
    seen: dict[str, str] = {}
    text_columns = ["bolge_adi", "sehir", "ulke", "tr_vize", "us_vize", "en_iyi_mevsim"]

    for row in rows:
        original_city = row.get("sehir", "")
        ascii_city = ascii_text(original_city)
        if ascii_city in seen and seen[ascii_city] != original_city:
            raise ValueError(
                f"City name collision after ASCII normalization: "
                f"{seen[ascii_city]!r} and {original_city!r} -> {ascii_city!r}"
            )
        seen[ascii_city] = original_city
        name_map[original_city] = ascii_city

        for column in text_columns:
            if column in row:
                row[column] = ascii_text(row[column])

    write_csv(path, rows, list(rows[0].keys()))
    return set(name_map), name_map


def choose_duplicate(
    current_original: str,
    current_value: Any,
    candidate_original: str,
    candidate_value: Any,
    preferred_original_names: set[str],
) -> tuple[str, Any]:
    current_preferred = current_original in preferred_original_names
    candidate_preferred = candidate_original in preferred_original_names
    if candidate_preferred and not current_preferred:
        return candidate_original, candidate_value
    if current_preferred and not candidate_preferred:
        return current_original, current_value

    current_len = len(str(current_value))
    candidate_len = len(str(candidate_value))
    if candidate_len > current_len:
        return candidate_original, candidate_value
    return current_original, current_value


def standardize_keyed_json(path: Path, preferred_original_names: set[str]) -> int:
    if not path.exists():
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return 0

    merged: dict[str, tuple[str, Any]] = {}
    duplicate_count = 0
    for original_key, value in data.items():
        key = ascii_text(original_key)
        if key in merged:
            duplicate_count += 1
            kept_original, kept_value = choose_duplicate(
                merged[key][0],
                merged[key][1],
                original_key,
                value,
                preferred_original_names,
            )
            merged[key] = (kept_original, kept_value)
        else:
            merged[key] = (original_key, value)

    normalized = {key: value for key, (_, value) in sorted(merged.items())}
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return duplicate_count


def standardize_cities_json() -> None:
    path = DATA / "cities.json"
    if not path.exists():
        return
    cities = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cities, list):
        return
    for city in cities:
        if not isinstance(city, dict):
            continue
        for key in ["id", "name", "country"]:
            if key in city:
                city[key] = ascii_text(city[key])
        if "route_id" in city:
            city["route_id"] = ascii_text(city["route_id"])
    path.write_text(json.dumps(cities, ensure_ascii=False, indent=2), encoding="utf-8")


def standardize_regions_json() -> None:
    path = DATA / "regions.json"
    if not path.exists():
        return
    regions = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(regions, list):
        return
    for region in regions:
        if not isinstance(region, dict):
            continue
        for key in ["id", "name"]:
            if key in region:
                region[key] = ascii_text(region[key])
        if "country_scope" in region and isinstance(region["country_scope"], list):
            region["country_scope"] = [ascii_text(value) for value in region["country_scope"]]
        if "sub_destinations" in region and isinstance(region["sub_destinations"], list):
            region["sub_destinations"] = [
                ascii_text(value) for value in region["sub_destinations"]
            ]
    path.write_text(json.dumps(regions, ensure_ascii=False, indent=2), encoding="utf-8")


def standardize_training_csv() -> None:
    path = DATA / "kullanici_veri.csv"
    if not path.exists():
        return
    rows = read_csv(path)
    if not rows:
        return
    for row in rows:
        if "oneri_sehir" in row:
            row["oneri_sehir"] = ascii_text(row["oneri_sehir"])
    write_csv(path, rows, list(rows[0].keys()))


def main() -> None:
    preferred_names, name_map = standardize_destination_catalog()
    duplicates = {
        "sehir_metinleri.json": standardize_keyed_json(
            DATA / "sehir_metinleri.json", preferred_names
        ),
        "sehir_aciklamalari.json": standardize_keyed_json(
            DATA / "sehir_aciklamalari.json", preferred_names
        ),
    }
    standardize_cities_json()
    standardize_regions_json()
    standardize_training_csv()

    changed = {old: new for old, new in name_map.items() if old != new}
    print(f"Standardized {len(name_map)} catalog city names.")
    print(f"Changed city names: {len(changed)}")
    for old, new in sorted(changed.items())[:40]:
        print(f"  {old} -> {new}")
    for file_name, count in duplicates.items():
        print(f"Resolved {count} duplicate ASCII keys in {file_name}.")


if __name__ == "__main__":
    main()
