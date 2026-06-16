"""sync_cities.py — cities.json ↔ model_destinasyonlar.csv senkronizasyon aracı.

cities.json tek kaynak; CSV onun türevidir.

Modlar:
  python scripts/sync_cities.py              # ad + vektör drift raporu
  python scripts/sync_cities.py --fix        # cities.json → CSV yeniden üret
  python scripts/sync_cities.py --absorb     # CSV → cities.json yaz (tek seferlik ters sync)
  python scripts/sync_cities.py --threshold 0.05  # drift eşiğini ayarla
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
CITIES_JSON = ROOT / "data" / "cities.json"
CSV_PATH    = ROOT / "data" / "model_destinasyonlar.csv"

FIZIK_FEATURES = ["deniz", "doga", "tarih", "kultur", "doga_spor", "su_spor", "hava_spor", "kis_spor"]
SOSYAL_FEATURES = ["eglence", "sakin", "yemek", "ulasim_kolayligi", "fiyat"]
ALL_FEATURES = FIZIK_FEATURES + SOSYAL_FEATURES


# ── helpers ───────────────────────────────────────────────────────────────────

def load_cities() -> list[dict]:
    with open(CITIES_JSON, encoding="utf-8") as f:
        return json.load(f)


def city_json_vectors(city: dict) -> dict[str, float]:
    phys = city.get("physical_vector", {})
    soc  = city.get("sociological_vector", {})
    return {f: float(phys.get(f, soc.get(f, 0.0))) for f in ALL_FEATURES}


def cities_to_df(cities: list[dict]) -> pd.DataFrame:
    rows = []
    for city in cities:
        vecs = city_json_vectors(city)
        row: dict = {
            "id":       city.get("id", city.get("name", "")),
            "sehir":    city.get("name", city.get("id", "")),
            "region_id": city.get("route_id", ""),
            "country":  city.get("country", ""),
            "visa_free": city.get("visa_free", True),
            "mevsim":   city.get("mevsim", 0),
        }
        row.update(vecs)
        rows.append(row)
    cols = (["id", "sehir", "region_id", "country", "visa_free"]
            + FIZIK_FEATURES + SOSYAL_FEATURES + ["mevsim"])
    return pd.DataFrame(rows, columns=cols)


def vector_diffs(
    json_vecs: dict[str, float],
    csv_row: pd.Series,
    threshold: float,
) -> dict[str, tuple[float, float]]:
    diffs = {}
    for f in ALL_FEATURES:
        if f not in csv_row.index:
            continue
        j_val = json_vecs.get(f, 0.0)
        c_val = float(csv_row[f])
        if abs(c_val - j_val) > threshold:
            diffs[f] = (round(j_val, 3), round(c_val, 3))
    return diffs


# ── report ────────────────────────────────────────────────────────────────────

def report(cities: list[dict], csv_df: pd.DataFrame, threshold: float) -> int:
    """Print drift report. Returns number of drifted cities."""
    json_map = {c.get("name", c.get("id", "")): c for c in cities}
    csv_names = set(csv_df["sehir"].dropna())
    json_names = set(json_map.keys())

    only_json = json_names - csv_names
    only_csv  = csv_names - json_names
    issues = 0

    if only_json:
        print(f"[NAME] cities.json'da var, CSV'de yok ({len(only_json)}):")
        for n in sorted(only_json):
            print(f"  + {n}")
        issues += len(only_json)

    if only_csv:
        print(f"[NAME] CSV'de var, cities.json'da yok ({len(only_csv)}):")
        for n in sorted(only_csv):
            print(f"  - {n}")
        issues += len(only_csv)

    vec_drifts: dict[str, dict] = {}
    for name, city in json_map.items():
        csv_rows = csv_df[csv_df["sehir"] == name]
        if csv_rows.empty:
            continue
        diffs = vector_diffs(city_json_vectors(city), csv_rows.iloc[0], threshold)
        if diffs:
            vec_drifts[name] = diffs

    if vec_drifts:
        print(f"\n[VEC]  Vektör drift > {threshold}: {len(vec_drifts)} şehir")
        for name, diffs in sorted(vec_drifts.items()):
            print(f"  {name}:")
            for feat, (j, c) in diffs.items():
                arrow = "▲" if c > j else "▼"
                print(f"    {feat}: json={j} {arrow} csv={c}")
        issues += len(vec_drifts)
    else:
        print(f"[VEC]  Vektör drift yok (eşik={threshold}).")

    if not issues:
        print(f"\nOK — {len(json_names)} şehir tam senkronda.")
    else:
        print(f"\n{issues} sorun tespit edildi. --fix veya --absorb ile düzeltin.")
    return issues


# ── fix (JSON → CSV) ──────────────────────────────────────────────────────────

def fix(cities: list[dict]) -> None:
    """Regenerate model_destinasyonlar.csv from cities.json (canonical direction)."""
    csv_df: pd.DataFrame | None = None
    if CSV_PATH.exists():
        csv_df = pd.read_csv(CSV_PATH)

    df = cities_to_df(cities)

    # Preserve quality-layer columns that may exist in current CSV
    if csv_df is not None:
        quality_cols = [c for c in csv_df.columns if c in ("safety", "pollution", "livability", "health_risk")]
        for col in quality_cols:
            if col not in df.columns:
                merge = csv_df[["sehir", col]].drop_duplicates("sehir")
                df = df.merge(merge, on="sehir", how="left")

    df.to_csv(CSV_PATH, index=False)
    print(f"[FIX] CSV yeniden üretildi: {len(df)} şehir → {CSV_PATH}")


# ── absorb (CSV → JSON) ───────────────────────────────────────────────────────

def absorb(cities: list[dict], csv_df: pd.DataFrame, threshold: float) -> None:
    """Write enriched CSV feature values back into cities.json (one-time reverse sync).

    Only updates features that differ by more than threshold — preserves unchanged values.
    """
    json_map = {c.get("name", c.get("id", "")): i for i, c in enumerate(cities)}
    updated = 0

    for _, csv_row in csv_df.iterrows():
        name = str(csv_row.get("sehir", ""))
        idx = json_map.get(name)
        if idx is None:
            continue

        city = cities[idx]
        phys = city.setdefault("physical_vector", {})
        soc  = city.setdefault("sociological_vector", {})
        json_vecs = city_json_vectors(city)
        diffs = vector_diffs(json_vecs, csv_row, threshold)

        if not diffs:
            continue

        for feat, (_, csv_val) in diffs.items():
            if feat in FIZIK_FEATURES:
                phys[feat] = round(csv_val, 3)
            else:
                soc[feat] = round(csv_val, 3)
        updated += 1

    with open(CITIES_JSON, "w", encoding="utf-8") as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)

    print(f"[ABSORB] {updated} şehir cities.json'a geri yazıldı → {CITIES_JSON}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="cities.json ↔ CSV senkronizasyon aracı")
    parser.add_argument("--fix",     action="store_true", help="cities.json → CSV yeniden üret")
    parser.add_argument("--absorb",  action="store_true", help="CSV vektörlerini → cities.json'a yaz")
    parser.add_argument("--threshold", type=float, default=0.05, help="Vektör drift eşiği (varsayılan: 0.05)")
    args = parser.parse_args()

    if not CITIES_JSON.exists():
        print(f"HATA: {CITIES_JSON} bulunamadı", file=sys.stderr)
        sys.exit(1)

    cities = load_cities()

    if not CSV_PATH.exists():
        if args.fix:
            fix(cities)
        else:
            print(f"CSV bulunamadı. Oluşturmak için: python scripts/sync_cities.py --fix")
            sys.exit(1)
        return

    csv_df = pd.read_csv(CSV_PATH)

    if args.absorb:
        absorb(cities, csv_df, args.threshold)
        # After absorb, also run report to confirm sync
        cities = load_cities()
        csv_df = pd.read_csv(CSV_PATH)
        report(cities, csv_df, args.threshold)
        return

    if args.fix:
        fix(cities)
        return

    # Default: drift report
    issues = report(cities, csv_df, args.threshold)
    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
