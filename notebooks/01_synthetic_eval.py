"""Synthetic user simulation and ablation for the current 8+5 vector model."""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from model.active_learning import select_next_pair as bald_select_next_pair  # noqa: E402
from model.config import (  # noqa: E402
    FEATURES,
    FIZIK_FEATURES,
    FIZIK_WEIGHTS,
    SOSYAL_FEATURES,
    SOSYAL_WEIGHTS,
)
from model.encoders import encode  # noqa: E402
from model.predict import (  # noqa: E402
    cosine_similarity,
    dual_skor,
    hybrid_skor,
    oneri_yap,
    sehirleri_yukle,
    weighted_cosine,
)
from model.region_vibe import update_vibe_emb  # noqa: E402


RNG_SEED = 42
RNG = np.random.default_rng(RNG_SEED)
N_OTURUM_PER_PERSONA = 50
PAIR_TURNS = 5

PERSONALAR = {
    "Deniz ve eglence": {"deniz": 0.9, "eglence": 0.85, "su_spor": 0.55, "yemek": 0.45},
    "Sakin sahil": {"deniz": 0.85, "sakin": 0.9, "doga": 0.45, "fiyat": 0.35},
    "Doga ve macera": {"doga": 0.9, "doga_spor": 0.85, "hava_spor": 0.45, "sakin": 0.55},
    "Tarih ve kultur": {"tarih": 0.95, "kultur": 0.9, "yemek": 0.55, "ulasim_kolayligi": 0.55},
    "Yemek ve sehir": {"yemek": 0.95, "kultur": 0.7, "eglence": 0.55, "ulasim_kolayligi": 0.75},
    "Kis ve dag": {"kis_spor": 0.95, "doga": 0.75, "doga_spor": 0.65, "fiyat": 0.55},
}


def persona_vektor(
    persona_def: dict,
    gurultu: float = 0.10,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    rng = rng or RNG
    v = np.array([persona_def.get(f, 0.05) for f in FEATURES], dtype=float)
    v += rng.normal(0, gurultu, size=v.shape)
    v = np.clip(v, 0.0, 1.0)
    return v[: len(FIZIK_FEATURES)], v[len(FIZIK_FEATURES):]


def city_vectors(row) -> tuple[np.ndarray, np.ndarray]:
    return (
        row[FIZIK_FEATURES].values.astype(float),
        row[SOSYAL_FEATURES].values.astype(float),
    )


def flat_vec(fiz: np.ndarray, sos: np.ndarray) -> np.ndarray:
    return np.concatenate([fiz, sos]).astype(float)


def flat_weights() -> np.ndarray:
    return np.array(
        [FIZIK_WEIGHTS[f] for f in FIZIK_FEATURES]
        + [SOSYAL_WEIGHTS[f] for f in SOSYAL_FEATURES],
        dtype=float,
    )


def ideal_set(df: pd.DataFrame, persona_def: dict, k: int = 8) -> set[str]:
    """Ground-truth proxy: top-k destinations for the clean persona vector."""
    u_fiz, u_sos = persona_vektor(persona_def, gurultu=0.0, rng=np.random.default_rng(RNG_SEED))
    scored = []
    for _, row in df.iterrows():
        s_fiz, s_sos = city_vectors(row)
        score = hybrid_skor(u_fiz, u_sos, s_fiz, s_sos, row.get("mevsim"), None)
        scored.append((row["sehir"], score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return {city for city, _ in scored[:k]}


def skor_baseline(u_fiz, u_sos, s_fiz, s_sos, row) -> float:
    return cosine_similarity(flat_vec(u_fiz, u_sos), flat_vec(s_fiz, s_sos))


def skor_weighted_flat(u_fiz, u_sos, s_fiz, s_sos, row) -> float:
    return weighted_cosine(flat_vec(u_fiz, u_sos), flat_vec(s_fiz, s_sos), flat_weights())


def skor_dual(u_fiz, u_sos, s_fiz, s_sos, row) -> float:
    score, _, _ = dual_skor(u_fiz, u_sos, s_fiz, s_sos, row.get("mevsim"), None)
    return score


def skor_hybrid(u_fiz, u_sos, s_fiz, s_sos, row) -> float:
    return hybrid_skor(u_fiz, u_sos, s_fiz, s_sos, row.get("mevsim"), None)


def ndcg_at_k(oneriler: list[str], dogru_set: set[str], k: int = 3) -> float:
    dcg = 0.0
    for i, sehir in enumerate(oneriler[:k]):
        rel = 1.0 if sehir in dogru_set else 0.0
        dcg += rel / np.log2(i + 2)
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(k, len(dogru_set))))
    return dcg / ideal if ideal > 0 else 0.0


def hit_at_k(oneriler: list[str], dogru_set: set[str], k: int = 3) -> float:
    return 1.0 if any(s in dogru_set for s in oneriler[:k]) else 0.0


def simulasyon_random(df: pd.DataFrame, n_per_persona: int = N_OTURUM_PER_PERSONA):
    rng = np.random.default_rng(RNG_SEED)
    truth = {name: ideal_set(df, pdef) for name, pdef in PERSONALAR.items()}
    cities = list(df["sehir"])
    ndcgs, hits = [], []
    for persona_ad in PERSONALAR:
        for _ in range(n_per_persona):
            top3 = list(rng.choice(cities, size=3, replace=False))
            ndcgs.append(ndcg_at_k(top3, truth[persona_ad], 3))
            hits.append(hit_at_k(top3, truth[persona_ad], 3))
    return float(np.mean(ndcgs)), float(np.mean(hits)), {}


def simulasyon_static_order(df: pd.DataFrame, n_per_persona: int = N_OTURUM_PER_PERSONA):
    truth = {name: ideal_set(df, pdef) for name, pdef in PERSONALAR.items()}
    top3 = list(df["sehir"].head(3))
    ndcgs, hits = [], []
    for persona_ad in PERSONALAR:
        for _ in range(n_per_persona):
            ndcgs.append(ndcg_at_k(top3, truth[persona_ad], 3))
            hits.append(hit_at_k(top3, truth[persona_ad], 3))
    return float(np.mean(ndcgs)), float(np.mean(hits)), {}


def simulasyon(df: pd.DataFrame, skor_fn, n_per_persona: int = N_OTURUM_PER_PERSONA):
    rng = np.random.default_rng(RNG_SEED)
    truth = {name: ideal_set(df, pdef) for name, pdef in PERSONALAR.items()}
    per_persona = {}
    for persona_ad, pdef in PERSONALAR.items():
        ndcgs, hits = [], []
        for _ in range(n_per_persona):
            u_fiz, u_sos = persona_vektor(pdef, rng=rng)
            scored = []
            for _, row in df.iterrows():
                s_fiz, s_sos = city_vectors(row)
                scored.append((row["sehir"], skor_fn(u_fiz, u_sos, s_fiz, s_sos, row)))
            scored.sort(key=lambda item: item[1], reverse=True)
            top3 = [city for city, _ in scored[:3]]
            ndcgs.append(ndcg_at_k(top3, truth[persona_ad], 3))
            hits.append(hit_at_k(top3, truth[persona_ad], 3))
        per_persona[persona_ad] = {"ndcg@3": float(np.mean(ndcgs)), "hit@3": float(np.mean(hits))}
    return (
        float(np.mean([m["ndcg@3"] for m in per_persona.values()])),
        float(np.mean([m["hit@3"] for m in per_persona.values()])),
        per_persona,
    )


def simulasyon_pipeline(df: pd.DataFrame, n_per_persona: int = N_OTURUM_PER_PERSONA):
    rng = np.random.default_rng(RNG_SEED)
    truth = {name: ideal_set(df, pdef) for name, pdef in PERSONALAR.items()}
    per_persona = {}
    for persona_ad, pdef in PERSONALAR.items():
        ndcgs, hits = [], []
        for _ in range(n_per_persona):
            u_fiz, u_sos = persona_vektor(pdef, rng=rng)
            top3 = [o["sehir"] for o in oneri_yap(u_fiz, u_sos, df, top_n=3, shuffle=False)]
            ndcgs.append(ndcg_at_k(top3, truth[persona_ad], 3))
            hits.append(hit_at_k(top3, truth[persona_ad], 3))
        per_persona[persona_ad] = {"ndcg@3": float(np.mean(ndcgs)), "hit@3": float(np.mean(hits))}
    return (
        float(np.mean([m["ndcg@3"] for m in per_persona.values()])),
        float(np.mean([m["hit@3"] for m in per_persona.values()])),
        per_persona,
    )


def _foto_pairs() -> list[dict]:
    with open(Path(PROJECT_ROOT) / "data" / "fotograflar.json", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("kategoriler", [])) + list(data.get("turlar", []))


def _side_vec(side: dict) -> tuple[np.ndarray, np.ndarray]:
    v = side.get("vektor", {})
    return (
        np.array([float(v.get(f, 0.0)) for f in FIZIK_FEATURES], dtype=float),
        np.array([float(v.get(f, 0.0)) for f in SOSYAL_FEATURES], dtype=float),
    )


def _photo_embeddings(pairs: list[dict]) -> dict[str, np.ndarray]:
    keys, texts = [], []
    for pair in pairs:
        for side in ("sol", "sag"):
            item = pair.get(side, {})
            key = Path(item.get("dosya", "")).stem
            text = item.get("aciklama", "").strip()
            if key and text:
                keys.append(key)
                texts.append(text)
    embs = encode(texts)
    return {key: emb for key, emb in zip(keys, embs, strict=False)}


def _region_embeddings() -> dict[str, np.ndarray]:
    with open(Path(PROJECT_ROOT) / "data" / "regions.json", encoding="utf-8") as f:
        regions = json.load(f)
    ids, texts = [], []
    for region in regions:
        text = " ".join(
            p for p in [region.get("hidden_description", ""), region.get("open_description", "")]
            if p
        ).strip()
        if region.get("id") and text:
            ids.append(region["id"])
            texts.append(text)
    embs = encode(texts)
    return {region_id: emb for region_id, emb in zip(ids, embs, strict=False)}


def _persona_text(persona_ad: str, pdef: dict) -> str:
    active = [f"{k}:{v:.2f}" for k, v in sorted(pdef.items()) if v >= 0.4]
    return f"{persona_ad} " + " ".join(active)


def _choose_side(persona_fiz, persona_sos, pair: dict) -> tuple[str, np.ndarray, np.ndarray]:
    l_fiz, l_sos = _side_vec(pair.get("sol", {}))
    r_fiz, r_sos = _side_vec(pair.get("sag", {}))
    l_score = weighted_cosine(flat_vec(persona_fiz, persona_sos), flat_vec(l_fiz, l_sos), flat_weights())
    r_score = weighted_cosine(flat_vec(persona_fiz, persona_sos), flat_vec(r_fiz, r_sos), flat_weights())
    return ("sol", l_fiz, l_sos) if l_score >= r_score else ("sag", r_fiz, r_sos)


def _simulate_pair_strategy(
    strategy: str,
    persona_ad: str,
    persona_def: dict,
    pairs: list[dict],
    region_embs: dict[str, np.ndarray],
    photo_embs: dict[str, np.ndarray],
    rng: np.random.Generator,
    turns: int = PAIR_TURNS,
) -> float:
    persona_fiz, persona_sos = persona_vektor(persona_def, gurultu=0.0, rng=rng)
    user_fiz = np.zeros(len(FIZIK_FEATURES), dtype=float)
    user_sos = np.zeros(len(SOSYAL_FEATURES), dtype=float)
    user_vibe = encode([_persona_text(persona_ad, persona_def)])[0]
    candidates = np.array(list(region_embs.values()), dtype=np.float32)
    shown: set[int] = set()

    bald_pairs = []
    for pair in pairs:
        left_key = Path(pair.get("sol", {}).get("dosya", "")).stem
        right_key = Path(pair.get("sag", {}).get("dosya", "")).stem
        bald_pairs.append((
            photo_embs.get(left_key, user_vibe),
            photo_embs.get(right_key, user_vibe),
        ))

    for _ in range(min(turns, len(pairs))):
        if strategy == "bald" and len(candidates) > 0:
            idx = bald_select_next_pair(user_vibe, candidates, bald_pairs, shown)
        else:
            unseen = [i for i in range(len(pairs)) if i not in shown]
            idx = int(rng.choice(unseen)) if unseen else None
        if idx is None:
            break
        shown.add(idx)
        side, chosen_fiz, chosen_sos = _choose_side(persona_fiz, persona_sos, pairs[idx])
        user_fiz = np.clip(user_fiz + 0.3 * (chosen_fiz - user_fiz), 0.0, 1.0)
        user_sos = np.clip(user_sos + 0.3 * (chosen_sos - user_sos), 0.0, 1.0)
        key = Path(pairs[idx].get(side, {}).get("dosya", "")).stem
        if key in photo_embs:
            user_vibe = update_vibe_emb(user_vibe, photo_embs[key])

    return weighted_cosine(flat_vec(persona_fiz, persona_sos), flat_vec(user_fiz, user_sos), flat_weights())


def ablation_bald_vs_random(n_per_persona: int = N_OTURUM_PER_PERSONA) -> dict[str, float]:
    pairs = _foto_pairs()
    photo_embs = _photo_embeddings(pairs)
    region_embs = _region_embeddings()
    rng_bald = np.random.default_rng(RNG_SEED)
    rng_random = np.random.default_rng(RNG_SEED)
    bald_scores, random_scores = [], []
    for persona_ad, pdef in PERSONALAR.items():
        for _ in range(n_per_persona):
            bald_scores.append(_simulate_pair_strategy(
                "bald", persona_ad, pdef, pairs, region_embs, photo_embs, rng_bald
            ))
            random_scores.append(_simulate_pair_strategy(
                "random", persona_ad, pdef, pairs, region_embs, photo_embs, rng_random
            ))
    return {
        "BALD mean persona cosine": float(np.mean(bald_scores)),
        "Random mean persona cosine": float(np.mean(random_scores)),
        "Delta": float(np.mean(bald_scores) - np.mean(random_scores)),
    }


def ablation_sorted_vs_shuffled_display(
    df: pd.DataFrame,
    n_per_persona: int = N_OTURUM_PER_PERSONA,
) -> dict[str, float]:
    rng = np.random.default_rng(RNG_SEED)
    truth = {name: ideal_set(df, pdef) for name, pdef in PERSONALAR.items()}
    sorted_ndcgs, shuffled_ndcgs, sorted_pick_positions, shuffled_pick_positions = [], [], [], []
    for persona_ad, pdef in PERSONALAR.items():
        for _ in range(n_per_persona):
            u_fiz, u_sos = persona_vektor(pdef, rng=rng)
            ranked = [o["sehir"] for o in oneri_yap(u_fiz, u_sos, df, top_n=3, shuffle=False)]
            shown = list(ranked)
            rng.shuffle(shown)
            sorted_ndcgs.append(ndcg_at_k(ranked, truth[persona_ad], 3))
            shuffled_ndcgs.append(ndcg_at_k(shown, truth[persona_ad], 3))
            pick = next((city for city in ranked if city in truth[persona_ad]), ranked[0])
            sorted_pick_positions.append(ranked.index(pick) + 1)
            shuffled_pick_positions.append(shown.index(pick) + 1)
    return {
        "Sorted NDCG@3": float(np.mean(sorted_ndcgs)),
        "Shuffled display NDCG@3": float(np.mean(shuffled_ndcgs)),
        "Sorted shown-position proxy": float(np.mean(sorted_pick_positions)),
        "Shuffled shown-position proxy": float(np.mean(shuffled_pick_positions)),
    }


def ablation_dual_vs_flat(df: pd.DataFrame) -> dict[str, float]:
    flat_ndcg, flat_hit, _ = simulasyon(df, skor_weighted_flat)
    dual_ndcg, dual_hit, _ = simulasyon(df, skor_dual)
    return {
        "Flat 13 NDCG@3": flat_ndcg,
        "Flat 13 Hit@3": flat_hit,
        "Dual 8+5 NDCG@3": dual_ndcg,
        "Dual 8+5 Hit@3": dual_hit,
        "NDCG Delta": dual_ndcg - flat_ndcg,
    }


def run_all(df: pd.DataFrame) -> dict:
    score_rows = []
    random_ndcg, random_hit, _ = simulasyon_random(df)
    static_ndcg, static_hit, _ = simulasyon_static_order(df)
    score_rows.extend([
        ("Random ranking", random_ndcg, random_hit),
        ("Static data order", static_ndcg, static_hit),
    ])
    senaryolar = [
        ("Baseline flat cosine", skor_baseline),
        ("Weighted flat cosine", skor_weighted_flat),
        ("Dual weighted cosine", skor_dual),
        ("Hybrid score", skor_hybrid),
    ]
    for ad, fn in senaryolar:
        ndcg, hit, _ = simulasyon(df, fn)
        score_rows.append((ad, ndcg, hit))
    ndcg, hit, detay = simulasyon_pipeline(df)
    score_rows.append(("Full oneri_yap pipeline", ndcg, hit))
    return {
        "score_rows": score_rows,
        "pipeline_detail": detay,
        "a1": ablation_bald_vs_random(),
        "a2": ablation_sorted_vs_shuffled_display(df),
        "a3": ablation_dual_vs_flat(df),
    }


def _write_metric_table(f, rows: list[tuple[str, float]]) -> None:
    f.write("| Metric | Value |\n|---|---:|\n")
    for name, value in rows:
        f.write(f"| {name} | {value:.3f} |\n")


def main() -> None:
    df = sehirleri_yukle()
    print(f"[Sim] {len(df)} destinasyon, {len(PERSONALAR)} persona, {N_OTURUM_PER_PERSONA} oturum/persona\n")
    results = run_all(df)

    print(f"{'Senaryo':<28} {'NDCG@3':>8} {'Hit@3':>8}")
    print("-" * 48)
    for ad, n, h in results["score_rows"]:
        print(f"{ad:<28} {n:>8.3f} {h:>8.3f}")

    rapor_yolu = os.path.join(PROJECT_ROOT, "notebooks", "ablation_sonuc.md")
    with open(rapor_yolu, "w", encoding="utf-8") as f:
        f.write("# Sentetik Ablation Sonuclari\n\n")
        f.write(f"- {len(df)} destinasyon, {len(PERSONALAR)} persona, {N_OTURUM_PER_PERSONA} oturum/persona\n")
        f.write("- Ground truth proxy: her persona icin hybrid skora gore en yakin 8 destinasyon\n")
        f.write(f"- Seed: {RNG_SEED}\n\n")
        f.write("## Skor Varyantlari\n\n")
        f.write("| Senaryo | NDCG@3 | Hit@3 |\n|---|---:|---:|\n")
        for ad, n, h in results["score_rows"]:
            f.write(f"| {ad} | {n:.3f} | {h:.3f} |\n")

        f.write("\n## A1 - BALD vs Random Pair\n\n")
        _write_metric_table(f, list(results["a1"].items()))

        f.write("\n## A2 - Sorted vs Shuffled Display\n\n")
        _write_metric_table(f, list(results["a2"].items()))

        f.write("\n## A3 - Dual 8+5 vs Flat 13\n\n")
        _write_metric_table(f, list(results["a3"].items()))

        f.write("\n## Full Pipeline Persona Kirilimi\n\n")
        f.write("| Persona | NDCG@3 | Hit@3 |\n|---|---:|---:|\n")
        for p, m in results["pipeline_detail"].items():
            f.write(f"| {p} | {m['ndcg@3']:.3f} | {m['hit@3']:.3f} |\n")
    print(f"\n[Sim] Rapor: {rapor_yolu}")


if __name__ == "__main__":
    main()
