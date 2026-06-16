"""Shared layout chrome for the Streamlit app."""

from __future__ import annotations

from datetime import datetime

import streamlit as st


STEP_ORDER = [
    ("giris", "Scope"),
    ("fotograf", "Photos"),
    ("region_pick", "Places"),
    ("anket_static", "Mood"),
    ("context", "Mood"),
    ("anket_adaptive", "Refine"),
    ("geri_bildirim", "Results"),
    ("oneri", "Results"),
]


def render_nav() -> None:
    if not st.session_state.get("lang_confirmed", False):
        st.markdown(
            """
            <div class="global-nav global-nav-minimal">
                <div class="brand-lockup">
                    <span class="brand-mark"></span>
                    <span class="brand-name">Discover</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    lang = st.session_state.get("lang", "TR")
    alt_lang = "EN" if lang == "TR" else "TR"
    st.markdown(
        f"""
        <div class="global-nav">
            <div class="brand-lockup">
                <span class="brand-mark"></span>
                <span class="brand-name">Discover</span>
            </div>
            <div class="nav-links">
                <span>Discover</span>
                <span>Curated</span>
                <span>About</span>
                <span class="nav-lang">{alt_lang}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    if not st.session_state.get("lang_confirmed", False):
        return

    st.markdown(
        """
        <footer class="app-footer">
            <span>Project</span>
            <span>Privacy</span>
            <span>Made with Streamlit</span>
            <span>v0.4</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )


def render_progress_rail() -> None:
    active = st.session_state.get("adim", "giris")
    active_index = next((i for i, (key, _) in enumerate(STEP_ORDER) if key == active), 0)
    unique_steps = [("giris", "Scope"), ("fotograf", "Photos"), ("region_pick", "Places"), ("context", "Mood"), ("geri_bildirim", "Results")]
    pool = 0
    df = st.session_state.get("filtered_df")
    if df is None:
        df = st.session_state.get("scope_filtered_df")
    if df is None:
        df = st.session_state.get("df")
    if df is not None:
        try:
            pool = len(df)
        except TypeError:
            pool = 0
    session_id = st.session_state.get("session_id") or "Trip 0042"
    started = datetime.now().strftime("%H:%M")
    rows = []
    for key, label in unique_steps:
        idx = next((i for i, (step_key, _) in enumerate(STEP_ORDER) if step_key == key), 0)
        cls = "done" if idx < active_index else ("active" if key == active or (key == "context" and active == "anket_adaptive") else "")
        dot = "●" if cls == "done" else ("◉" if cls == "active" else "○")
        rows.append(f'<div class="rail-step {cls}"><span>{dot}</span><b>{label}</b></div>')
    st.markdown(
        f"""
        <aside class="progress-rail">
            <div class="rail-kicker">{session_id}</div>
            <div class="rail-meta">Started {started}</div>
            <div class="rail-steps">{''.join(rows)}</div>
            <div class="rail-pool"><strong>{pool}</strong><span>places in pool</span></div>
        </aside>
        """,
        unsafe_allow_html=True,
    )
