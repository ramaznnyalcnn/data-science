"""ADIM 2.2 — Top-3 bölge multi-pick."""

from __future__ import annotations

import streamlit as st

from app.components.tutorial import render_tutorial
from app.utils import (
    _filter_regions_safe,
    _region_pick_commit,
    _region_summary,
    _region_title,
    _show_all_regions,
    _show_recommended_regions,
)


def render_region_pick() -> None:
    lang = st.session_state.get("lang", "TR")
    base_df = (
        st.session_state.scope_filtered_df
        if st.session_state.scope_filtered_df is not None
        else st.session_state.df
    )
    regions = st.session_state.regions
    show_all_regions = bool(st.session_state.get("show_all_regions", False))
    region_top_n = len(regions) if show_all_regions else 3

    st.session_state.top_regions = st.session_state.region_model.predict_regions(
        st.session_state.kullanici_fizik_v,
        st.session_state.kullanici_sosyal_v,
        base_df,
        regions,
        top_n=region_top_n,
    )

    top_regions = st.session_state.top_regions
    if not top_regions:
        st.warning(
            "Uygun bölge bulunamadı, tüm havuzla devam ediliyor."
            if lang == "TR"
            else "No suitable region was found, continuing with the full pool."
        )
        st.session_state.filtered_df = _filter_regions_safe(
            base_df, [], st.session_state.kullanici_sosyal_v, sort_by_social=True,
        )
        st.session_state.adim = "context"
        st.rerun()

    if show_all_regions:
        baslik = "Filtreye uygun tüm bölgeler" if lang == "TR" else "All regions matching filters"
        alt = (
            "Başlangıçtaki ülke/vize filtreleri korunuyor. Bir veya birkaç bölge seçebilirsin."
            if lang == "TR"
            else "Initial country/visa filters are preserved. Pick one or more regions."
        )
    else:
        baslik = "Aramayı üç rota grubuna daralttık" if lang == "TR" else "We've narrowed your search to three places"
        alt = (
            "İlgini çekenleri kısa listeye ekle; ham uyum yüzdesi yerine rota hissine odaklanıyoruz."
            if lang == "TR"
            else "Add the ones that feel right; the raw match score stays behind the interface."
        )

    st.markdown(f"""
    <div class="flow-title">
        <h2>{baslik}</h2>
        <p>{alt}</p>
    </div>
    <hr style="margin:0.5rem 0 1.5rem 0">
    """, unsafe_allow_html=True)
    render_tutorial("region_pick", lang)

    selected_region_ids = []
    for row_start in range(0, len(top_regions), 3):
        row = top_regions[row_start: row_start + 3]
        cols = st.columns(len(row))
        for col, region in zip(cols, row):
            key = f"region_pick_{region['id']}"
            is_checked = bool(st.session_state.get(key, False))
            with col:
                checked = st.checkbox(
                    "+ Kısa listeye ekle" if lang == "TR" else "+ Add to shortlist",
                    value=is_checked,
                    key=key,
                )
                card_class = "option-card selected" if checked else "option-card"
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="option-card-title">{_region_title(region)}</div>
                        <div class="option-card-desc">{_region_summary(region)}</div>
                        <div class="option-card-meta">5 places · 4-7 nights</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if checked:
                    selected_region_ids.append(region["id"])

    if not selected_region_ids:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); '
            f'padding:0.8rem 1.2rem; text-align:center; margin-top:0.8rem;">'
            f'<span style="color:var(--warning); font-weight:700; font-size:0.95rem;">'
            f'{"Devam etmek için en az bir bölge seçmelisin." if lang == "TR" else "You must select at least one region to continue."}'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    col_continue, col_all = st.columns([1.5, 1])
    shown_region_ids = [r["id"] for r in top_regions]
    with col_continue:
        st.button(
            "Bu bölgelerle devam et →" if lang == "TR" else "Continue with these regions →",
            type="primary",
            width="stretch",
            disabled=not selected_region_ids,
            key="region_continue_selected",
            on_click=_region_pick_commit,
            args=(selected_region_ids, shown_region_ids, 0),
        )

    with col_all:
        if show_all_regions:
            st.button(
                "Önerilen üç bölgeye dön" if lang == "TR" else "Back to top 3 regions",
                width="stretch",
                key="region_show_recommended",
                on_click=_show_recommended_regions,
            )
        else:
            st.button(
                "Tüm 25 bölgeyi göster" if lang == "TR" else "Show all 25 regions",
                width="stretch",
                key="region_show_all_filtered",
                on_click=_show_all_regions,
            )
