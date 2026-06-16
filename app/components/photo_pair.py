"""ADIM 2 — Fotoğraf karşılaştırması."""

from __future__ import annotations

import os

import streamlit as st

from model.config import FEATURES, FIZIK_FEATURES, GUVEN_ESIGI, MAX_FOTO, MIN_FOTO, SOSYAL_FEATURES
from model.predict import (
    adaptif_soru_sec,
    fizik_vektore_cevir,
    guven_skoru_hesapla,
    kullanici_vektoru_guncelle,
    sosyal_vektore_cevir,
)
from model.region_vibe import update_vibe_emb
from app.components.layout import render_progress_rail
from app.components.tutorial import render_tutorial
from app.lang import t
from app.utils import _foto_aciklama, _preference_vector_html

FOTO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "photos"))


def render_fotograf() -> None:
    df            = st.session_state.filtered_df if st.session_state.filtered_df is not None else st.session_state.df
    kullanici_fiz = st.session_state.kullanici_fizik_v
    kullanici_sos = st.session_state.kullanici_sosyal_v
    gosterilen    = st.session_state.gosterilen
    kategoriler   = st.session_state.kategoriler
    turlar        = st.session_state.turlar
    lang          = st.session_state.get("lang", "TR")

    st.markdown("""
    <style>
    @media (min-width: 701px) {
        div[data-testid="stImage"] img {
            height: min(68vh, 720px) !important;
            min-height: 520px !important;
            object-fit: cover !important;
        }
    }
    @media (max-width: 700px) {
        div[data-testid="stImage"] img {
            height: auto !important;
            max-height: 36vh !important;
            object-fit: cover !important;
        }
        .photo-caption {
            min-height: auto !important;
            padding: 0.7rem 0.75rem !important;
            margin-bottom: 0.65rem !important;
        }
        .photo-caption-text {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    tur_idx = st.session_state.tur
    guven   = guven_skoru_hesapla(
        kullanici_fiz, kullanici_sos, df, gosterilen,
        st.session_state.kullanici_mevsim,
    )

    if not st.session_state.kategori_secildi and kategoriler:
        if tur_idx < len(kategoriler):
            tur = kategoriler[tur_idx]
        else:
            st.session_state.kategori_secildi = True
            st.session_state.tur = 0
            st.rerun()
    else:
        gosterilmis_set = st.session_state.gosterilmis_tur_idxler
        min_tamamlandi  = gosterilen >= MIN_FOTO
        guven_yeterli   = guven >= GUVEN_ESIGI
        max_doldu       = gosterilen >= MAX_FOTO
        tur_bitti       = len(gosterilmis_set) >= len(turlar)

        if min_tamamlandi and (guven_yeterli or max_doldu or tur_bitti):
            st.session_state.top_regions = []
            st.session_state.adim = "region_pick"
            st.rerun()

        if st.session_state.aktif_tur_idx is None:
            secilen_idx = adaptif_soru_sec(
                kullanici_fiz, kullanici_sos, df, turlar,
                gosterilmis_set, st.session_state.kullanici_mevsim,
                user_vibe_emb=st.session_state.get("kullanici_vibe_emb"),
                photo_embs=st.session_state.get("photo_embs"),
                region_embs=st.session_state.get("region_embs"),
            )
            st.session_state.aktif_tur_idx = secilen_idx if secilen_idx is not None else 0
        tur_idx = st.session_state.aktif_tur_idx
        tur = turlar[tur_idx]

    sol = tur["sol"]
    sag = tur["sag"]
    soru_metni = (tur.get("soru_en", tur.get("soru", "")) if lang == "EN"
                  else tur.get("soru", t("which_draws", lang)))

    total_questions = max(MAX_FOTO, gosterilen + 1)
    dots = "".join(
        f'<span class="progress-dot {"filled" if i <= gosterilen else ""}"></span>'
        for i in range(MAX_FOTO)
    )
    st.markdown(f"""
    <div class="question-meta">Question {gosterilen + 1} of {total_questions}</div>
    <div class="progress-dots">{dots}</div>
    <div class="soru-baslik">
        <h2>{soru_metni}</h2>
        <p>{t('instinct_note', lang)}</p>
    </div>
    """, unsafe_allow_html=True)
    render_tutorial("fotograf", lang)

    rail_col, stage_col = st.columns([0.23, 0.77])
    with rail_col:
        render_progress_rail()
    with stage_col:
        col_sol, col_sag = st.columns(2)

    def foto_goster(col, taraf, foto_bilgi, label_icon):
        with col:
            foto_yolu = os.path.join(FOTO_DIR, foto_bilgi["dosya"])
            if os.path.exists(foto_yolu):
                st.image(foto_yolu, width="stretch")
            else:
                st.markdown(
                    f"""
                    <div style="
                        height:560px; border:1px solid var(--border); background:var(--linen);
                        display:flex; align-items:center; justify-content:center;
                        text-align:center; padding:1rem; color:var(--text-muted);
                        font-size:0.95rem; line-height:1.4;
                    ">{_foto_aciklama(foto_bilgi, lang)}</div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown(f"""
            <div class="photo-caption">
                <div class="photo-caption-title">{'Place A' if taraf == 'sol' else 'Place B'}</div>
                <div class="photo-caption-text">{_foto_aciklama(foto_bilgi, lang)}</div>
            </div>
            """, unsafe_allow_html=True)
            return st.button(
                "Choose" if lang == "EN" else "Seç",
                key=f"btn_{taraf}_{tur_idx}",
                type="primary",
                width="stretch",
            )

    with stage_col:
        sec_sol = foto_goster(col_sol, "sol", sol, "")
        sec_sag = foto_goster(col_sag, "sag", sag, "")
        st.caption("Skip is available by continuing through the visual set." if lang == "EN" else "Kararsızsan bir sonraki görsel çiftine seçim yaparak ilerleyebilirsin.")

    if sec_sol or sec_sag:
        secilen = sol if sec_sol else sag
        v_dict  = secilen["vektor"]

        yeni_fiz = kullanici_vektoru_guncelle(
            st.session_state.kullanici_fizik_v, fizik_vektore_cevir(v_dict)
        )
        yeni_sos = kullanici_vektoru_guncelle(
            st.session_state.kullanici_sosyal_v, sosyal_vektore_cevir(v_dict)
        )
        st.session_state.kullanici_fizik_v  = yeni_fiz
        st.session_state.kullanici_sosyal_v = yeni_sos

        # Vibe embedding EMA güncelle (BALD Stage 1 için ayrı kanal)
        photo_embs = st.session_state.get("photo_embs")
        if photo_embs and st.session_state.get("kullanici_vibe_emb") is not None:
            from pathlib import Path
            key = Path(secilen.get("dosya", "")).stem
            emb = photo_embs.get(key)
            if emb is not None:
                st.session_state.kullanici_vibe_emb = update_vibe_emb(
                    st.session_state.kullanici_vibe_emb, emb
                )

        if not st.session_state.kategori_secildi:
            st.session_state.tur += 1
        else:
            tur_idx_aktif = st.session_state.aktif_tur_idx
            aktif_tur = turlar[tur_idx_aktif] if tur_idx_aktif is not None else None

            if aktif_tur and aktif_tur.get("mevsim_sinyal"):
                mevsim_val = (sol if sec_sol else sag).get("mevsim")
                if mevsim_val is not None:
                    st.session_state.kullanici_mevsim = int(mevsim_val)

            gosterilmis_set = st.session_state.gosterilmis_tur_idxler
            gosterilmis_set.add(tur_idx_aktif)
            st.session_state.gosterilmis_tur_idxler = gosterilmis_set
            st.session_state.aktif_tur_idx = None
            st.session_state.gosterilen += 1
        st.rerun()

    if gosterilen > 0:
        with st.expander("Tercih vektörünü göster (şeffaflık)"):
            st.markdown(
                _preference_vector_html(kullanici_fiz, kullanici_sos, lang),
                unsafe_allow_html=True,
            )
