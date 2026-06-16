"""ADIM 2.7 / 2.8 / 2.5 — Statik anket, context, adaptif anket."""

from __future__ import annotations

import numpy as np
import streamlit as st

from model import context_matcher as ctx_matcher
from model.adaptive_survey import (
    apply_answer_update,
    questions_skipped_by_context,
    survey_should_stop,
)
from model.config import FIZIK_FEATURES, QUALITY_FEATURES, SOSYAL_FEATURES
from app.components.tutorial import render_tutorial
from app.utils import _preference_vector_html


def render_anket_static() -> None:
    lang   = st.session_state.get("lang", "TR")
    survey = st.session_state.static_survey
    idx    = st.session_state.static_survey_index

    if not survey:
        st.warning("Statik anket bulunamadı." if lang == "TR" else "Static survey was not found.")
        st.session_state.adim = "anket_adaptive"
        st.rerun()

    if idx >= len(survey):
        st.session_state.adim = "anket_adaptive"
        st.rerun()

    question = survey[idx]
    st.markdown(f"""
    <div class="flow-title">
        <h2>{'Kısa anket' if lang == 'TR' else 'Short survey'}</h2>
        <p>{'Soru' if lang == 'TR' else 'Question'} {idx + 1} / {len(survey)}</p>
    </div>
    <hr style="margin:0.5rem 0 1.5rem 0">
    """, unsafe_allow_html=True)
    render_tutorial("anket_static", lang)

    st.subheader(question.get("text", {}).get(lang) or question.get("text", {}).get("TR", ""))
    answers = question.get("answers", [])
    options = [answer.get("id") for answer in answers]
    labels = {
        answer.get("id"): answer.get("label", {}).get(lang) or answer.get("label", {}).get("TR", answer.get("id", ""))
        for answer in answers
    }
    selected = st.radio(
        "Yanıt seç" if lang == "TR" else "Choose an answer",
        options,
        format_func=lambda key: labels.get(key, key),
        index=None,
        key=f"static_answer_{question.get('id')}",
        label_visibility="collapsed",
    )

    if st.button(
        "Devam →" if lang == "TR" else "Continue →",
        type="primary",
        width="stretch",
        disabled=selected is None,
    ):
        answer = next(item for item in answers if item.get("id") == selected)
        new_fiz, new_sos = apply_answer_update(
            st.session_state.kullanici_fizik_v,
            st.session_state.kullanici_sosyal_v,
            answer.get("vector", {}),
            blend=0.62,
        )
        qid = question.get("id")
        st.session_state.kullanici_fizik_v = new_fiz
        st.session_state.kullanici_sosyal_v = new_sos
        st.session_state.static_survey_answers = {
            **st.session_state.static_survey_answers,
            qid: selected,
        }
        st.session_state.static_survey_index = idx + 1
        if st.session_state.static_survey_index >= len(survey):
            st.session_state.adim = "anket_adaptive"
        st.rerun()


def render_context() -> None:
    lang = st.session_state.get("lang", "TR")

    st.markdown(f"""
    <div class="flow-title">
        <h2>{'Sana en yakın tatil hissini seç' if lang == 'TR' else 'Choose the trip feeling closest to you'}</h2>
        <p>{'Birkaç kart seçebilirsin. İstersen kartların altına kendi cümleni de yaz.' if lang == 'TR' else 'Pick a few cards. You can also add your own sentence below.'}</p>
    </div>
    <hr style="margin:0.5rem 0 1.5rem 0">
    """, unsafe_allow_html=True)
    render_tutorial("context", lang)

    if st.button(
        "← Bölge seçimine geri dön" if lang == "TR" else "← Back to region choice",
        key="back_to_region_pick",
        width="stretch",
    ):
        st.session_state.adim = "region_pick"
        st.rerun()

    try:
        presets_data = ctx_matcher.load_presets()
    except Exception as e:
        st.error(f"Preset yüklenemedi: {e}")
        presets_data = {}

    preset_list = list(presets_data.values())
    selected_ids = list(st.session_state.get("context_preset_picks", []))
    max_presets = 3
    st.caption(
        f"En fazla {max_presets} kart seçebilirsin." if lang == "TR" else f"Pick up to {max_presets} cards."
    )

    cols_per_row = 3
    for row_start in range(0, len(preset_list), cols_per_row):
        row = preset_list[row_start: row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, p in zip(cols, row):
            with col:
                is_sel = p["id"] in selected_ids
                can_pick = is_sel or len(selected_ids) < max_presets
                checked = st.checkbox(
                    "Seç" if lang == "TR" else "Select",
                    value=is_sel,
                    key=f"preset_chk_{p['id']}",
                    disabled=not can_pick,
                )
                if checked and p["id"] not in selected_ids:
                    selected_ids.append(p["id"])
                elif not checked and p["id"] in selected_ids:
                    selected_ids.remove(p["id"])
                card_class = "option-card selected" if checked else "option-card"
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="option-card-title">{p['label']}</div>
                        <div class="option-card-desc">{p['text'][:105]}{'...' if len(p['text']) > 105 else ''}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.session_state.context_preset_picks = selected_ids

    text_value = st.text_area(
        "Veya kendin yaz..." if lang == "TR" else "Or write your own...",
        value=st.session_state.get("context_text", ""),
        height=140,
        key="context_text_input",
        placeholder=(
            "Sakin sahil, iyi yemek, gece hayatı az olsun. Bütçem orta."
            if lang == "TR"
            else "Calm coast, good food, light nightlife, mid budget."
        ),
    )

    col_next, col_skip = st.columns([1.35, 1])
    with col_next:
        if st.button(
            "Devam et →" if lang == "TR" else "Continue →",
            type="primary",
            width="stretch",
            disabled=not selected_ids and not (text_value or "").strip(),
            key="ctx_btn_combined",
        ):
            text_clean = (text_value or "").strip()
            method_parts = []
            final_result = None
            if selected_ids:
                result = ctx_matcher.from_presets(selected_ids)
                st.session_state.kullanici_fizik_v, st.session_state.kullanici_sosyal_v = ctx_matcher.blend_into_user(
                    st.session_state.kullanici_fizik_v,
                    st.session_state.kullanici_sosyal_v,
                    result,
                    blend=0.40,
                )
                final_result = result
                method_parts.append("preset")
            if text_clean:
                with st.spinner("Anlamsal eşleşme..." if lang == "TR" else "Semantic matching..."):
                    result = ctx_matcher.from_nlp(text_clean)
                st.session_state.kullanici_fizik_v, st.session_state.kullanici_sosyal_v = ctx_matcher.blend_into_user(
                    st.session_state.kullanici_fizik_v,
                    st.session_state.kullanici_sosyal_v,
                    result,
                    blend=0.28 if selected_ids else 0.35,
                )
                if final_result is None:
                    final_result = result
                else:
                    final_result.known_dims = set(final_result.known_dims) | set(result.known_dims)
                    final_result.top_presets = list(final_result.top_presets or []) + list(result.top_presets or [])
                    final_result.top_regions = result.top_regions or final_result.top_regions
                    final_result.confidence = max(float(final_result.confidence), float(result.confidence))
                method_parts.append("nlp")

            if final_result is None:
                final_result = ctx_matcher.from_skip()
                method_parts = ["skip"]

            method = "+".join(method_parts)
            st.session_state.context_method = method
            st.session_state.context_text = text_clean
            st.session_state.context_partial_fizik = final_result.partial_fizik
            st.session_state.context_partial_sosyal = final_result.partial_sosyal
            st.session_state.context_known_dims = final_result.known_dims
            st.session_state.context_top_presets = final_result.top_presets
            st.session_state.context_top_regions = final_result.top_regions or []
            st.session_state.context_confidence = final_result.confidence
            st.session_state.top_regions = []

            sl = st.session_state.get("session_logger")
            if sl is not None:
                sl.log_context(
                    method=method,
                    nlp_text=text_clean or None,
                    nlp_top_regions=final_result.top_regions or [],
                    nlp_top_presets=final_result.top_presets or [],
                    preset_picks=selected_ids,
                    partial_fizik=final_result.partial_fizik.tolist(),
                    partial_sosyal=final_result.partial_sosyal.tolist(),
                    confidence=final_result.confidence,
                )
            st.session_state.adim = "anket_adaptive"
            st.rerun()

    with col_skip:
        if st.button(
            "Bunları seçmek istemiyorum, devam et" if lang == "TR" else "Skip these and continue",
            width="stretch",
            key="ctx_btn_skip",
        ):
            result = ctx_matcher.from_skip()
            st.session_state.context_method = "skip"
            st.session_state.context_text = ""
            st.session_state.context_partial_fizik = result.partial_fizik
            st.session_state.context_partial_sosyal = result.partial_sosyal
            st.session_state.context_known_dims = set()
            st.session_state.context_confidence = 0.0
            st.session_state.top_regions = []
            sl = st.session_state.get("session_logger")
            if sl is not None:
                sl.log_context(
                    method="skip",
                    nlp_text=None,
                    nlp_top_regions=[],
                    nlp_top_presets=[],
                    preset_picks=[],
                    partial_fizik=None,
                    partial_sosyal=None,
                    confidence=0.0,
                )
            st.session_state.adim = "anket_adaptive"
            st.rerun()


def render_anket_adaptive() -> None:
    lang = st.session_state.get("lang", "TR")
    df   = st.session_state.filtered_df if st.session_state.filtered_df is not None else st.session_state.df
    pool = st.session_state.question_pool
    asked_ids    = st.session_state.asked_question_ids
    kullanici_fiz = st.session_state.kullanici_fizik_v
    kullanici_sos = st.session_state.kullanici_sosyal_v

    if survey_should_stop(asked_ids, kullanici_fiz, kullanici_sos, df):
        st.session_state.top_regions = []
        st.session_state.adim = "geri_bildirim"
        st.rerun()

    if not pool:
        st.warning("Soru havuzu bulunamadı." if lang == "TR" else "Question pool was not found.")
        st.session_state.top_regions = []
        st.session_state.adim = "geri_bildirim"
        st.rerun()

    skip_dims = set(st.session_state.get("context_known_dims") or set())
    survey_model = st.session_state.survey_model
    active_id = st.session_state.active_question_id
    question = next((q for q in pool if q.get("id") == active_id), None)
    if question is None:
        question = survey_model.select_question(
            kullanici_fiz, kullanici_sos, df, pool, asked_ids, skip_dims=skip_dims
        )
        if question is None:
            st.session_state.top_regions = []
            st.session_state.adim = "geri_bildirim"
            st.rerun()
        st.session_state.active_question_id = question.get("id")
        st.session_state.active_answer_pair = None

    answers = question.get("answers", [])
    answer_by_id = {answer.get("id"): answer for answer in answers}
    pair_ids = st.session_state.get("active_answer_pair")
    if not pair_ids or any(answer_id not in answer_by_id for answer_id in pair_ids):
        left, right = survey_model.select_answer_pair(question, kullanici_fiz, kullanici_sos, df)
        if left is None or right is None:
            st.session_state.top_regions = []
            st.session_state.adim = "geri_bildirim"
            st.rerun()
        pair_ids = [left.get("id"), right.get("id")]
        st.session_state.active_answer_pair = pair_ids

    total = min(5, max(3, len(asked_ids) + 1))
    st.markdown(f"""
    <div class="flow-title">
        <h2>{'Adaptive Pairwise Anket' if lang == 'TR' else 'Adaptive Pairwise Survey'}</h2>
        <p>{'Soru' if lang == 'TR' else 'Question'} {len(asked_ids) + 1} / {total}</p>
    </div>
    <hr style="margin:0.5rem 0 1.5rem 0">
    """, unsafe_allow_html=True)
    render_tutorial("anket_adaptive", lang)

    question_text = question.get("text", {}).get(lang) or question.get("text", {}).get("TR", "")
    st.subheader(question_text)
    st.markdown(
        f"<p style='color:var(--slate); font-size:1.05rem; margin-top:-0.35rem'>"
        f"{'Hangisi sana daha yakın?' if lang == 'TR' else 'Which one is closer to you?'}</p>",
        unsafe_allow_html=True,
    )

    pair_answers = [answer_by_id[pair_ids[0]], answer_by_id[pair_ids[1]]]
    selected = None
    cols = st.columns(2)
    for col, answer in zip(cols, pair_answers):
        label = answer.get("label", {}).get(lang) or answer.get("label", {}).get("TR", answer.get("id", ""))
        with col:
            st.markdown(
                f"""
                <div class="option-card" style="min-height:135px; margin-bottom:0.75rem">
                    <div class="option-card-title">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Bunu seç" if lang == "TR" else "Choose this",
                key=f"pairwise_answer_{question.get('id')}_{answer.get('id')}",
                width="stretch",
            ):
                selected = answer.get("id")

    skip_selected = st.button(
        "Bu ikisi de uymadı, soruyu geç" if lang == "TR" else "Neither fits, skip this question",
        key=f"pairwise_skip_{question.get('id')}_{'_'.join(pair_ids)}",
        width="stretch",
    )

    if selected is not None or skip_selected:
        qid = question.get("id")
        if selected is not None:
            answer = answer_by_id[selected]
            answer_vector = answer.get("vector", {})
            new_fiz, new_sos = survey_model.apply_choice(
                st.session_state.kullanici_fizik_v,
                st.session_state.kullanici_sosyal_v,
                answer,
            )
            st.session_state.kullanici_fizik_v = new_fiz
            st.session_state.kullanici_sosyal_v = new_sos
            quality_values = [
                float(answer_vector.get(feature, 0.0))
                for feature in QUALITY_FEATURES
                if feature in answer_vector
            ]
            if quality_values and float(np.mean(quality_values)) >= 0.68:
                st.session_state.prefer_safety = True
        else:
            new_fiz = st.session_state.kullanici_fizik_v
            new_sos = st.session_state.kullanici_sosyal_v
        st.session_state.asked_question_ids = asked_ids + [qid]
        st.session_state.survey_answers = {**st.session_state.survey_answers, qid: selected or "none"}
        st.session_state.survey_pairwise_turns = st.session_state.get("survey_pairwise_turns", []) + [{
            "question_id": qid,
            "shown_answers": list(pair_ids),
            "picked": selected,
            "skipped": bool(skip_selected),
        }]
        st.session_state.active_question_id = None
        st.session_state.active_answer_pair = None
        if survey_should_stop(st.session_state.asked_question_ids, new_fiz, new_sos, df):
            sl = st.session_state.get("session_logger")
            if sl is not None:
                skipped = questions_skipped_by_context(pool, st.session_state.asked_question_ids, skip_dims)
                sl.log_survey(
                    asked_qids=st.session_state.asked_question_ids,
                    skipped_qids=skipped,
                    skip_reason={s: "context_known" for s in skipped},
                    answers=st.session_state.survey_answers,
                    answer_vector_delta={},
                    pairwise_turns=st.session_state.get("survey_pairwise_turns", []),
                )
            st.session_state.top_regions = []
            st.session_state.adim = "geri_bildirim"
        st.rerun()

    with st.expander("Tercih vektörünü göster (şeffaflık)" if lang == "TR" else "Show preference vector"):
        st.markdown(
            _preference_vector_html(kullanici_fiz, kullanici_sos, lang),
            unsafe_allow_html=True,
        )
