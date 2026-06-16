"""Guardrails against leaking destination names in hidden recommendation copy."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).parent.parent


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_name(text: str, name: str) -> bool:
    normalized_text = f" {_norm(text)} "
    normalized_name = _norm(name)
    if not normalized_name:
        return False
    return f" {normalized_name} " in normalized_text


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_region_hidden_descriptions_do_not_name_own_destinations():
    regions = _load_json(ROOT / "data" / "regions.json")
    leaks = []
    for region in regions:
        hidden = region.get("hidden_description", "")
        for city in region.get("sub_destinations", []):
            if _contains_name(hidden, city):
                leaks.append(f"{region.get('id')} -> {city}")
    assert not leaks, "Region hidden descriptions leak cities: " + ", ".join(leaks[:20])


def test_city_hidden_summaries_do_not_name_city():
    for rel_path in ["data/hidden_summaries.json", "data/city_curated_summaries.json"]:
        data = _load_json(ROOT / rel_path)
        leaks = []
        for city, item in data.items():
            hidden_parts = [
                item.get("hidden_title", ""),
                item.get("hidden_summary", ""),
                " ".join(item.get("hidden_tags", [])),
            ]
            hidden_text = " ".join(hidden_parts)
            if _contains_name(hidden_text, city):
                leaks.append(city)
        assert not leaks, f"{rel_path} hidden copy leaks city names: {leaks[:20]}"
