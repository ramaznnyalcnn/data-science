"""Build city vector adjustment layer from anonymous session feedback.

This is intentionally conservative for the course-project prototype:
- selected cities get a small positive adjustment toward the user's final vector
- shown but unselected cities get a very small negative adjustment
- quality feedback can nudge safety/livability down when suggestions were rejected

The base dataset stays unchanged. The output is written to
data/city_dynamic_adjustments.json and is applied by model.predict.sehirleri_yukle().
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SESSIONS = DATA / "sessions.jsonl"
DESTINATIONS = DATA / "model_destinasyonlar.csv"
OUTPUT = DATA / "city_dynamic_adjustments.json"

FEATURES = [
    "deniz", "doga", "tarih", "kultur",
    "doga_spor", "su_spor", "hava_spor", "kis_spor",
    "eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat",
    "safety", "pollution", "livability", "health_risk",
]


def _load_sessions() -> list[dict]:
    if not SESSIONS.exists():
        return []
    rows = []
    with SESSIONS.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> None:
    if not DESTINATIONS.exists():
        raise SystemExit(f"Missing {DESTINATIONS}")

    df = pd.read_csv(DESTINATIONS)
    by_city = df.set_index("sehir")
    accum: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, int] = defaultdict(int)

    for session in _load_sessions():
        stage2 = session.get("stage2_cities", {})
        picked = stage2.get("user_pick")
        shown = stage2.get("shown_order", [])
        feedback = session.get("stage3_feedback", {})
        satisfaction = str(feedback.get("satisfaction", "")).lower()

        if picked in by_city.index:
            counts[picked] += 1
            for feature in FEATURES:
                if feature in by_city.columns:
                    value = float(by_city.at[picked, feature])
                    accum[picked][feature] += (value - 0.5) * 0.006

        for city in shown:
            if city == picked or city not in by_city.index:
                continue
            counts[city] += 1
            for feature in FEATURES:
                if feature in by_city.columns:
                    value = float(by_city.at[city, feature])
                    accum[city][feature] -= (value - 0.5) * 0.0015

        if satisfaction in {"uygun değil", "not a fit", "hayir", "hayır"}:
            for city in shown:
                if city in by_city.index:
                    accum[city]["safety"] -= 0.002
                    accum[city]["livability"] -= 0.002

    out = {
        "_meta": {
            "description": "Generated from data/sessions.jsonl by scripts/update_dynamic_city_adjustments.py",
            "session_count": len(_load_sessions()),
            "city_count": len(accum),
        },
        "cities": {},
    }
    for city, values in sorted(accum.items()):
        clipped = {
            feature: round(max(min(delta, 0.08), -0.08), 4)
            for feature, delta in values.items()
            if abs(delta) >= 0.0005
        }
        if clipped:
            out["cities"][city] = clipped

    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} from {len(_load_sessions())} sessions")


if __name__ == "__main__":
    main()
