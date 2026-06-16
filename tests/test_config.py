"""Schema invariants for the 8+5 recommendation vectors and 25 regions."""

import json
from pathlib import Path

from model.config import FEATURES, FIZIK_FEATURES, REGIONS, SOSYAL_FEATURES


def test_feature_dimensions_match_plan():
    assert len(FIZIK_FEATURES) == 8
    assert len(SOSYAL_FEATURES) == 5
    assert len(FEATURES) == 13


def test_regions_match_regions_json():
    regions_path = Path(__file__).parent.parent / "data" / "regions.json"
    with open(regions_path, encoding="utf-8") as f:
        regions = json.load(f)

    expected = {region["id"] for region in regions}
    assert len(REGIONS) == 25
    assert set(REGIONS) == expected


def test_region_destinations_are_loaded():
    assert all(isinstance(destinations, list) for destinations in REGIONS.values())
    assert all(destinations for destinations in REGIONS.values())
