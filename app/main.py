"""
Adaptif Pairwise Karşılaştırma ile Kişiselleştirilmiş Gezi Yeri Öneri Sistemi
Streamlit arayüzü — router / orchestrator
"""

import importlib
import json
import os
import sys

import numpy as np
import streamlit as st

# Proje kök dizinini Python yoluna ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model.adaptive_pairwise_model import AdaptivePairwiseRegionModel
from model.adaptive_pairwise_survey_model import AdaptivePairwiseSurveyModel
from model.adaptive_survey import load_question_pool
from model.predict import sehirleri_yukle
from model.recommend import load_ranker
from model.region_ranker import load_regions
from model.region_vibe import load_photo_embeddings, load_region_embeddings

from app.components.city_list import render_geri_bildirim
from app.components.layout import render_footer, render_nav
from app.components.multi_pick import render_region_pick
from app.components.photo_pair import render_fotograf
from app.components.reveal import render_giris
from app.components.survey import render_anket_adaptive, render_anket_static, render_context
from app.state import state_baslat
from app.styles import CSS

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


# ── Process-singleton cache yardımcıları ─────────────────
@st.cache_data(show_spinner=False)
def _load_json_cached(path: str, mtime: float):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def _cached_sehirler():
    return sehirleri_yukle()


@st.cache_resource(show_spinner=False)
def _cached_ranker():
    return load_ranker()


@st.cache_resource(show_spinner=False)
def _cached_photo_embeddings():
    return load_photo_embeddings()


@st.cache_resource(show_spinner=False)
def _cached_region_embeddings():
    return load_region_embeddings()


@st.cache_resource(show_spinner=False)
def _cached_question_pool(path: str, mtime: float):
    return load_question_pool(path)


@st.cache_resource(show_spinner=False)
def _cached_regions(path: str, mtime: float):
    return load_regions(path)


def _load_json(path: str):
    return _load_json_cached(path, os.path.getmtime(path))


# ── Sayfa ayarı ──────────────────────────────────────────
st.set_page_config(
    page_title="Gezi Rehberi",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Session state başlat ──────────────────────────────────
state_baslat()

# ── Veri yükle (lazy, session-cache) ─────────────────────
if st.session_state.df is None:
    _metin_json = os.path.join(DATA_DIR, "sehir_metinleri.json")
    _dest_csv   = os.path.join(DATA_DIR, "destinasyonlar.csv")
    _should_regen = False
    if os.path.exists(_metin_json) and os.path.exists(_dest_csv):
        if os.path.getmtime(_metin_json) > os.path.getmtime(_dest_csv):
            _should_regen = True
    if _should_regen:
        try:
            _nlp_mod = importlib.import_module("model.nlp_sehir_profili")
            with st.spinner("Destinasyon profilleri güncelleniyor..."):
                _metinler = _load_json(_metin_json)
                _nlp_df = _nlp_mod.sehir_profillerini_uret(_metinler)
                _nlp_df.to_csv(_dest_csv, index=False)
                _cached_sehirler.clear()
        except Exception as _nlp_err:
            st.warning(f"NLP güncelleme atlandı: {_nlp_err}")
    st.session_state.df = _cached_sehirler()

if st.session_state.model is None:
    st.session_state.model = _cached_ranker()

if "region_model" not in st.session_state:
    st.session_state.region_model = AdaptivePairwiseRegionModel()

if "survey_model" not in st.session_state:
    st.session_state.survey_model = AdaptivePairwiseSurveyModel()

if not st.session_state.turlar:
    foto_json = os.path.join(DATA_DIR, "fotograflar.json")
    _foto_data = _load_json(foto_json)
    st.session_state.turlar    = _foto_data.get("turlar", [])
    st.session_state.kategoriler = _foto_data.get("kategoriler", [])

if not st.session_state.photo_embs:
    st.session_state.photo_embs = _cached_photo_embeddings()

if not st.session_state.region_embs:
    st.session_state.region_embs = _cached_region_embeddings()

if st.session_state.kullanici_vibe_emb is None and st.session_state.region_embs:
    _region_matrix = np.array(list(st.session_state.region_embs.values()), dtype=np.float32)
    _centroid = _region_matrix.mean(axis=0)
    _norm = float(np.linalg.norm(_centroid))
    if _norm > 0.0:
        st.session_state.kullanici_vibe_emb = (_centroid / _norm).astype(np.float32)

if not st.session_state.embedding_warning:
    if not st.session_state.photo_embs or not st.session_state.region_embs:
        st.session_state.embedding_warning = (
            "Embedding artifacts missing; Stage 1 uses heuristic fallback. "
            "Run scripts/build_photo_embeddings.py and scripts/build_region_embeddings.py."
        )
        print(f"[EMB] {st.session_state.embedding_warning}")

if not st.session_state.question_pool:
    soru_json = os.path.join(DATA_DIR, "question_pool.json")
    if os.path.exists(soru_json):
        st.session_state.question_pool = _cached_question_pool(soru_json, os.path.getmtime(soru_json))

if not st.session_state.regions:
    regions_json = os.path.join(DATA_DIR, "regions.json")
    if os.path.exists(regions_json):
        st.session_state.regions = _cached_regions(regions_json, os.path.getmtime(regions_json))

if not st.session_state.aciklamalar:
    curated_json = os.path.join(DATA_DIR, "city_curated_summaries.json")
    hidden_json  = os.path.join(DATA_DIR, "hidden_summaries.json")
    acik_json    = os.path.join(DATA_DIR, "sehir_aciklamalari.json")
    if os.path.exists(curated_json) or os.path.exists(hidden_json):
        summary_path = curated_json if os.path.exists(curated_json) else hidden_json
        hidden_data = _load_json(summary_path)
        st.session_state.aciklamalar = {
            city: {
                "TR": item.get("hidden_summary", ""),
                "EN": item.get("hidden_summary", ""),
                "reveal": item.get("reveal_summary", ""),
                "title": item.get("hidden_title", ""),
                "tags": item.get("hidden_tags", []),
            }
            for city, item in hidden_data.items()
        }
    elif os.path.exists(acik_json):
        st.session_state.aciklamalar = _load_json(acik_json)

# ── Router ───────────────────────────────────────────────
adim = st.session_state.adim
render_nav()

if adim == "giris":
    render_giris()
elif adim == "fotograf":
    render_fotograf()
elif adim == "region_pick":
    render_region_pick()
elif adim == "anket_static":
    render_anket_static()
elif adim == "context":
    render_context()
elif adim == "anket_adaptive":
    render_anket_adaptive()
elif adim in ("oneri", "geri_bildirim"):
    render_geri_bildirim()

render_footer()
