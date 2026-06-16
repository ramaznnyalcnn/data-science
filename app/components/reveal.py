"""ADIM 1 — Giriş / scope seçimi."""

from __future__ import annotations

import streamlit as st

from model.scope_filter import (
    SCOPE_ABROAD, SCOPE_MIXED, SCOPE_TURKEY,
    VISA_FREE, VISA_INCLUDE_REQUIRED,
    filter_destinations, needs_visa_filter,
)
from model.session_logger import SessionLogger
from model.config import FIZIK_FEATURES, SOSYAL_FEATURES
from app.components.tutorial import render_tutorial
from app.lang import t
from app.utils import _reset_city_stage_state


def _render_language_gate() -> None:
    st.markdown(
        """
        <section class="language-gate" aria-label="Language selection">
            <div class="language-gate-copy">
                <div class="language-gate-kicker">Language / Dil</div>
                <h1>Choose your language</h1>
                <p>Uygulamaya devam etmek için önce dili seç. Diğer adımlar seçimden sonra açılır.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    col_tr, col_en = st.columns(2)
    with col_tr:
        if st.button("Türkçe", key="choose_lang_tr", type="primary", width="stretch"):
            st.session_state.lang = "TR"
            st.session_state.lang_confirmed = True
            st.rerun()
    with col_en:
        if st.button("English", key="choose_lang_en", type="primary", width="stretch"):
            st.session_state.lang = "EN"
            st.session_state.lang_confirmed = True
            st.rerun()


def render_giris() -> None:
    lang = st.session_state.get("lang", "TR")

    if not st.session_state.get("lang_confirmed", False):
        _render_language_gate()
        return

    hero_title = "Discover<br>where you'd<br>actually go" if lang == "EN" else "Gerçekten<br>gideceğin yeri<br>keşfet"
    hero_sub = (
        "Popüler listelerin değil, kısa bir görsel testin ve yolculuk hissinin yönettiği sade bir kısa liste."
        if lang == "TR"
        else "Not where everyone else is going. A short visual test, then a shortlist curated to your instinct."
    )
    st.markdown(
        f"""
        <section class="editorial-hero">
            <div class="hero-copy">
                <div class="hero-title">{hero_title}</div>
                <p class="hero-sub">{hero_sub}</p>
                <div class="hero-note">3 minutes · No account · Anonymous session</div>
            </div>
            <div class="hero-photo" aria-hidden="true"></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    render_tutorial("giris", lang)

    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        st.markdown(
            f'<div class="section-kicker">{"Where to look?" if lang == "EN" else "Nereye bakalım?"}</div>',
            unsafe_allow_html=True,
        )
        scope_labels = {
            None: "Seçim yap" if lang == "TR" else "Choose",
            SCOPE_MIXED: "Both" if lang == "EN" else "TR + World",
            SCOPE_TURKEY: "TR" if lang == "EN" else "Türkiye",
            SCOPE_ABROAD: "World" if lang == "EN" else "Dünya",
        }
        scope_options = [None, SCOPE_MIXED, SCOPE_TURKEY, SCOPE_ABROAD]
        current_scope = st.session_state.get("scope_mode")
        if current_scope not in scope_options:
            current_scope = None
        st.session_state.scope_mode = st.radio(
            "Öneri havuzu" if lang == "TR" else "Recommendation pool",
            scope_options,
            index=scope_options.index(current_scope),
            format_func=lambda key: scope_labels[key],
            horizontal=True,
        )
    with col_b2:
        needs_visa = st.session_state.scope_mode is not None and needs_visa_filter(
            st.session_state.df, st.session_state.scope_mode
        )
        if needs_visa:
            st.markdown(
                f'<div class="section-kicker">{"Visa preference" if lang == "EN" else "Vize tercihi"}</div>',
                unsafe_allow_html=True,
            )
            visa_labels = {
                None: "Seçim yap" if lang == "TR" else "Choose",
                VISA_FREE: "Vizesiz" if lang == "TR" else "Visa-free only",
                VISA_INCLUDE_REQUIRED: "Vize dahil" if lang == "TR" else "Include visa",
            }
            visa_options = [None, VISA_FREE, VISA_INCLUDE_REQUIRED]
            current_visa = st.session_state.get("visa_mode")
            if current_visa not in visa_options:
                current_visa = None
            st.session_state.visa_mode = st.radio(
                "Yurtdışı vize tercihi" if lang == "TR" else "Abroad visa preference",
                visa_options,
                index=visa_options.index(current_visa),
                format_func=lambda key: visa_labels[key],
                horizontal=True,
            )
        else:
            st.session_state.visa_mode = VISA_FREE

    st.markdown(
        f'<div class="section-kicker">{"Travel safety" if lang == "EN" else "Güvenlik ve konfor"}</div>',
        unsafe_allow_html=True,
    )
    col_safe, _ = st.columns([1.4, 0.6])
    with col_safe:
        st.session_state.prefer_safety = st.checkbox(
            "Daha güvenli ve temiz yerleri öne çıkar" if lang == "TR"
            else "Prioritize safer, cleaner places",
            value=st.session_state.get("prefer_safety", False),
        )
        if st.session_state.prefer_safety:
            safety_defaults = {
                "safety": 0.92, "pollution": 0.88,
                "livability": 0.78, "health_risk": 0.84,
            }
            for feature, value in safety_defaults.items():
                if feature in SOSYAL_FEATURES:
                    idx = SOSYAL_FEATURES.index(feature)
                    st.session_state.kullanici_sosyal_v[idx] = max(
                        float(st.session_state.kullanici_sosyal_v[idx]), value,
                    )

    btn_lbl = t("start_btn", lang)
    can_start = st.session_state.scope_mode is not None and (
        not needs_visa or st.session_state.visa_mode is not None
    )
    if not can_start:
        st.caption(
            "Başlamak için öneri havuzu ve gerekiyorsa vize tercihini seç."
            if lang == "TR"
            else "Choose a recommendation pool and visa preference if needed before starting."
        )
    if st.button(btn_lbl, type="primary", width="stretch", disabled=not can_start):
        active_df = filter_destinations(
            st.session_state.df,
            st.session_state.scope_mode,
            st.session_state.visa_mode,
        )
        if active_df.empty:
            st.error(
                "Bu filtreyle uygun destinasyon bulunamadı."
                if lang == "TR"
                else "No destinations match this filter."
            )
            st.stop()
        st.session_state.filtered_df = active_df
        st.session_state.scope_filtered_df = active_df
        st.session_state.oneriler = []
        st.session_state.reveal = False
        st.session_state.gosterilen = 0
        st.session_state.gosterilmis_tur_idxler = set()
        st.session_state.aktif_tur_idx = None
        st.session_state.asked_question_ids = []
        st.session_state.survey_answers = {}
        st.session_state.active_question_id = None
        st.session_state.top_regions = []
        st.session_state.selected_region_ids = []
        st.session_state.static_survey_index = 0
        st.session_state.static_survey_answers = {}
        st.session_state.show_all_cities = False
        st.session_state.show_all_regions = False
        _reset_city_stage_state()
        st.session_state.free_text_vibe = ""
        st.session_state.free_text_confidence = 0.0
        sl = SessionLogger()
        sl.start(scope={
            "scope_mode": st.session_state.scope_mode,
            "visa_mode":  st.session_state.visa_mode,
        })
        st.session_state.session_logger = sl
        st.session_state.session_id = sl.session_id
        st.session_state.adim = "fotograf"
        st.rerun()
