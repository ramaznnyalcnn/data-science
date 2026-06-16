"""ADIM 4 — Geri bildirim / şehir seçimi."""

from __future__ import annotations

import random

import numpy as np
import streamlit as st

from model.config import FEATURES, FIZIK_FEATURES, SOSYAL_FEATURES
from model.recommend import recommend_places
from app.components.tutorial import render_tutorial
from app.utils import (
    _compact_html,
    _html_escape,
    _kaydet,
    _oneri_aciklama,
    _reset_city_stage_state,
    _user_profile_html,
    _yeniden_baslat,
)


def _dots(value: float) -> str:
    filled = max(1, min(5, int(round(float(value) * 5))))
    return "●" * filled + "○" * (5 - filled)


def render_geri_bildirim() -> None:
    lang          = st.session_state.get("lang", "TR")
    kullanici_fiz = st.session_state.kullanici_fizik_v
    kullanici_sos = st.session_state.kullanici_sosyal_v
    df            = st.session_state.filtered_df if st.session_state.filtered_df is not None else st.session_state.df
    aciklamalar   = st.session_state.aciklamalar

    baslik = "Kısa listen hazır" if lang == "TR" else "Your shortlist is ready"
    alt = (
        "10 yer, sıralama ima etmiyor. Açıklamalara göre sana yakın gelenleri seç."
        if lang == "TR"
        else "10 places, no order implied. Choose the places that feel right from their descriptions."
    )
    alt_html = "<br>".join(_html_escape(part) for part in alt.splitlines())
    st.markdown(_compact_html(f"""
    <div style="text-align:center; padding:1.5rem 0 0.8rem">
        <h2 style="font-family:Fraunces, Georgia, serif; color:var(--ink); font-weight:700; margin:0.3rem 0; font-size:2.3rem">{_html_escape(baslik)}</h2>
        <p style="color:var(--slate); font-size:1.05rem; line-height:1.45">{alt_html}</p>
    </div>
    <hr style="margin:0.5rem 0 1.2rem 0">
    """), unsafe_allow_html=True)
    render_tutorial("geri_bildirim", lang)
    st.markdown(_user_profile_html(kullanici_fiz, kullanici_sos, lang), unsafe_allow_html=True)

    tum_sehirler = recommend_places(
        kullanici_fiz,
        kullanici_sos,
        df,
        top_n=len(df),
        model=st.session_state.get("model"),
        aciklamalar=aciklamalar,
        u_mevsim=st.session_state.kullanici_mevsim,
        prefer_safety=st.session_state.get("prefer_safety", False),
        shuffle=False,
    )

    ILK_ADAY_SAYISI = 10
    MAX_SECIM = 5
    show_all = st.session_state.get("show_all_cities", False)
    revealed_selected = st.session_state.get("stage2_revealed_selected", [])

    ranked_names = [o["sehir"] for o in tum_sehirler]
    top_ranked_names = ranked_names[:ILK_ADAY_SAYISI]
    ranked_key = tuple((o["sehir"], o.get("skor")) for o in tum_sehirler[:ILK_ADAY_SAYISI])
    if (
        st.session_state.get("stage2_ranked_key") != ranked_key
        or not st.session_state.get("stage2_shown_order")
    ):
        shown_names = list(top_ranked_names)
        random.shuffle(shown_names)
        st.session_state.stage2_ranked_key = ranked_key
        st.session_state.stage2_shown_order = shown_names
    shown_names = list(st.session_state.stage2_shown_order)
    by_name = {o["sehir"]: o for o in tum_sehirler}
    if show_all:
        remaining_names = [name for name in ranked_names if name not in shown_names]
        display_names = shown_names + remaining_names
        gosterilecek_sehirler = [by_name[n] for n in display_names if n in by_name]
    else:
        display_names = shown_names
        gosterilecek_sehirler = [by_name[n] for n in shown_names if n in by_name]

    selected_names = {
        oneri["sehir"]
        for oneri in gosterilecek_sehirler
        if st.session_state.get(f"chk_{oneri['sehir']}", False)
    }
    secilen = []

    for row_start in range(0, len(gosterilecek_sehirler), 2):
        row = gosterilecek_sehirler[row_start: row_start + 2]
        grid_cols = st.columns(len(row))
        for offset, (col, oneri) in enumerate(zip(grid_cols, row)):
            i = row_start + offset
            aciklama  = _oneri_aciklama(oneri, lang)
            cumle     = aciklama.split(".")[0] + "." if "." in aciklama else aciklama
            devam     = aciklama[len(cumle):].strip()
            skor_fiz  = min(oneri.get("skor_fizik",  0) / 0.55, 1.0)
            skor_sos  = min(oneri.get("skor_sosyal", 0) / 0.45, 1.0)

            is_selected = oneri["sehir"] in selected_names
            card_class = "shortlist-card selected" if is_selected else "shortlist-card"

            with col:
                limit_doldu = len(selected_names) >= MAX_SECIM
                option_label = (
                    f"Seçenek {i + 1} seç" if lang == "TR" else f"Select option {i + 1}"
                )
                secildi = st.checkbox(
                    option_label,
                    key=f"chk_{oneri['sehir']}",
                    disabled=limit_doldu and not st.session_state.get(f"chk_{oneri['sehir']}", False),
                )
                if secildi:
                    secilen.append(oneri["sehir"])
                devam_kisa = devam[:210] + "..." if len(devam) > 210 else devam
                card_html = _compact_html(f"""
                <div class="{card_class}" style="margin-bottom:1rem">
                    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:0.7rem">
                        <div style="color:var(--primary); font-size:0.78rem; font-weight:800; text-transform:uppercase">
                            {_html_escape('Seçenek' if lang == 'TR' else 'Place')} {i + 1}
                        </div>
                        <div class="dot-rating">{_dots((skor_fiz + skor_sos) / 2)}</div>
                    </div>
                    <div style="color:var(--ink); font-size:1.14rem; font-weight:800;
                                line-height:1.42; margin-bottom:0.55rem">{_html_escape(cumle)}</div>
                    <div style="color:var(--slate); font-size:0.98rem; line-height:1.55; margin-bottom:0.8rem">
                        {_html_escape(devam_kisa)}
                    </div>
                    <div style="display:grid; grid-template-columns:86px 1fr; gap:0.35rem 0.8rem; color:var(--slate); font-size:0.86rem; border-top:1px solid var(--border); padding-top:0.75rem">
                        <span>Route fit</span><span class="dot-rating">{_dots(skor_fiz)}</span>
                        <span>Mood fit</span><span class="dot-rating">{_dots(skor_sos)}</span>
                    </div>
                </div>
                """)
                st.markdown(card_html, unsafe_allow_html=True)

    if not show_all and len(tum_sehirler) > ILK_ADAY_SAYISI:
        daha_fazla = (
            "Bunlar uymadıysa diğer şehirleri göster"
            if lang == "TR"
            else "If these do not fit, show other cities"
        )
        if st.button(daha_fazla, width="stretch"):
            st.session_state.show_all_cities = True
            st.rerun()

    st.markdown("<hr style='margin:1.5rem 0 1rem 0'>", unsafe_allow_html=True)

    limit_metni = f"(en fazla {MAX_SECIM})" if lang == "TR" else f"(max {MAX_SECIM})"
    if secilen:
        ozet = f"{len(secilen)}/{MAX_SECIM} yer seçildi" if lang == "TR" else f"{len(secilen)}/{MAX_SECIM} places selected"
        st.markdown(f'<p style="color:var(--success); font-weight:700; margin-bottom:0.8rem">{ozet}</p>',
                    unsafe_allow_html=True)
    else:
        st.caption(f'{"En az 1, " + limit_metni + " seçim yap" if lang == "TR" else "Select at least 1 " + limit_metni}')

    st.markdown("<div style='margin-top:0.9rem'></div>", unsafe_allow_html=True)
    feedback_options = (
        ["Uygun", "Kısmen uygun", "Uygun değil"]
        if lang == "TR"
        else ["Good fit", "Partly fit", "Not a fit"]
    )
    stage2_feedback = st.radio(
        "Bu bölümde gösterilen şehirler sana ne kadar uygundu?"
        if lang == "TR"
        else "How well did these city suggestions fit you?",
        feedback_options,
        index=None,
        horizontal=True,
        key="stage2_feedback",
    )
    feedback_comment = st.text_area(
        "Kısa geri dönüt (opsiyonel)" if lang == "TR" else "Short feedback (optional)",
        key="stage2_feedback_comment",
        height=90,
        placeholder=(
            "Örn. daha sakin şehirler beklerdim, kıyı şehirleri daha uygundu..."
            if lang == "TR"
            else "For example: I expected calmer places, coastal cities fit better..."
        ),
    )

    col1, col2 = st.columns(2)
    with col1:
        etiket = "Reveal & save →" if lang == "EN" else "Göster ve kaydet →"
        disabled = len(secilen) == 0 or stage2_feedback is None
        if st.button(etiket, type="primary", width="stretch", disabled=disabled):
            kullanici_v_combined = np.concatenate([kullanici_fiz, kullanici_sos])
            yuksek_eslesmeler = [o["sehir"] for o in tum_sehirler[:ILK_ADAY_SAYISI]]
            for sehir in secilen:
                _kaydet(kullanici_v_combined, sehir, begendi=1)
            for sehir in yuksek_eslesmeler:
                if sehir not in secilen:
                    _kaydet(kullanici_v_combined, sehir, begendi=0)

            sl = st.session_state.get("session_logger")
            if sl is not None:
                ranked_backend = [(o["sehir"], float(o.get("skor", 0.0))) for o in tum_sehirler[:ILK_ADAY_SAYISI]]
                if show_all:
                    shown_order = [o["sehir"] for o in gosterilecek_sehirler]
                else:
                    shown_order = list(st.session_state.get("stage2_shown_order", top_ranked_names))
                pick = secilen[0] if secilen else None
                click_pos = shown_order.index(pick) if pick in shown_order else None
                sl.log_stage2(
                    candidate_pool=[o["sehir"] for o in tum_sehirler],
                    ranked_backend=ranked_backend,
                    shown_order=shown_order,
                    click_position=click_pos,
                    user_pick=pick,
                    time_to_pick_s=None,
                )
                sl.log_feedback(
                    satisfaction=stage2_feedback,
                    would_book=bool(secilen),
                    comment=feedback_comment,
                    alt_pick=None,
                )
                try:
                    sl.flush()
                except Exception as _e:
                    print(f"[LOG] flush hata: {_e}")

            if secilen:
                hedef_fiz = np.zeros(len(FIZIK_FEATURES))
                hedef_sos = np.zeros(len(SOSYAL_FEATURES))
                for sehir in secilen:
                    satir = df[df["sehir"] == sehir]
                    if not satir.empty:
                        hedef_fiz += satir[FIZIK_FEATURES].values[0].astype(float)
                        hedef_sos += satir[SOSYAL_FEATURES].values[0].astype(float)
                hedef_fiz /= len(secilen)
                hedef_sos /= len(secilen)
                st.session_state.kullanici_fizik_v  = np.clip(kullanici_fiz * 0.4 + hedef_fiz * 0.6, 0.0, 1.0)
                st.session_state.kullanici_sosyal_v = np.clip(kullanici_sos * 0.4 + hedef_sos * 0.6, 0.0, 1.0)

            st.session_state.stage2_revealed_selected = list(secilen)
            st.success(
                "Kaydedildi. Seçtiğin yerler aşağıda açıldı."
                if lang == "TR"
                else "Saved. Your selected places are revealed below."
            )
    with col2:
        if st.button("Yeniden başla" if lang == "TR" else "Start over", width="stretch"):
            _yeniden_baslat()

    revealed_selected = st.session_state.get("stage2_revealed_selected", [])
    if revealed_selected:
        title = "Seçtiğin yerler" if lang == "TR" else "Your selected places"
        option_word = "Seçenek" if lang == "TR" else "Option"
        rows = ""
        for idx, sehir in enumerate(revealed_selected, start=1):
            rows += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'gap:1rem; padding:0.65rem 0; border-top:1px solid var(--border);">'
                f'<span style="color:var(--slate)">{_html_escape(option_word)} {idx}</span>'
                f'<b style="color:var(--ink)">{_html_escape(sehir)}</b>'
                f'</div>'
            )
        st.markdown(_compact_html(f"""
        <div style="background:var(--surface); border:1px solid var(--border);
                    padding:1rem 1.15rem; margin-top:1rem">
            <div class="reveal-city" style="color:var(--ink); font-size:1.35rem; font-weight:700; margin-bottom:0.35rem">
                {_html_escape(title)}
            </div>
            {rows}
        </div>
        """), unsafe_allow_html=True)
