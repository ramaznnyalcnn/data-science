"""Session state initialization."""

from __future__ import annotations

import numpy as np
import streamlit as st

from model.config import FIZIK_FEATURES, SOSYAL_FEATURES


def state_baslat() -> None:
    defaults = {
        "adim":               "giris",
        "lang":               "TR",
        "lang_confirmed":     False,
        "kullanici_fizik_v":  np.zeros(len(FIZIK_FEATURES)),
        "kullanici_sosyal_v": np.zeros(len(SOSYAL_FEATURES)),
        "kullanici_mevsim":   None,
        "tur":                0,
        "gosterilen":         0,
        "oneriler":           [],
        "df":                 None,
        "filtered_df":        None,
        "model":              None,
        "turlar":             [],
        "kategoriler":        [],
        "question_pool":      [],
        "static_survey":      [],
        "regions":            [],
        "scope_mode":         None,
        "visa_mode":          None,
        "aktif_sorular":      [],
        "kategori_secildi":   False,
        "gidilen":            [],
        "gb_yanit":           None,
        "aciklamalar":        {},
        "reveal":             False,
        "session_id":         None,
        "session_logger":     None,
        "show_all_cities":    False,
        "show_all_regions":   False,
        "prefer_safety":      False,
        "context_method":       None,
        "context_choice":       None,
        "context_text":         "",
        "context_preset_picks": [],
        "context_partial_fizik":  None,
        "context_partial_sosyal": None,
        "context_known_dims":   set(),
        "context_top_presets":  [],
        "context_top_regions":  [],
        "context_confidence":   0.0,
        "stage2_t0":            None,
        "stage2_feedback":      None,
        "stage2_feedback_comment": "",
        "gosterilmis_tur_idxler": set(),
        "aktif_tur_idx":      None,
        "asked_question_ids": [],
        "survey_answers":     {},
        "active_question_id": None,
        "active_answer_pair": None,
        "survey_pairwise_turns": [],
        "top_regions":        [],
        "selected_region_ids": [],
        "static_survey_index": 0,
        "static_survey_answers": {},
        "free_text_vibe":     "",
        "free_text_confidence": 0.0,
        "kullanici_vibe_emb": None,
        "photo_embs":         {},
        "region_embs":        {},
        "embedding_warning":   "",
        "scope_filtered_df":  None,
        "v2_adim":            "s1",
        "v2_agirliklar":      {
            "tarih": 0.5, "kultur": 0.5, "eglence": 0.5,
            "yemek": 0.5, "ulasim_kolayligi": 0.5, "fiyat": 0.5,
        },
        "v2_kazanan":         None,
        "v2_ikinci":          None,
        "v2_min":             None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
