"""Configuration guardrails for the Streamlit app."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_main_does_not_load_legacy_static_survey():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "docs\", \"legacy\", \"static_survey.json" not in source
    assert "legacy_static" not in source


def test_sessions_jsonl_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "data/sessions.jsonl" in gitignore


def test_language_gate_state_defaults_to_unconfirmed():
    source = (ROOT / "app" / "state.py").read_text(encoding="utf-8")

    assert '"lang_confirmed":     False' in source


def test_intro_returns_early_until_language_is_confirmed():
    source = (ROOT / "app" / "components" / "reveal.py").read_text(encoding="utf-8")

    assert "def _render_language_gate" in source
    assert 'st.session_state.lang_confirmed = True' in source
    assert 'if not st.session_state.get("lang_confirmed", False):' in source
    assert "_render_language_gate()\n        return" in source


def test_mobile_css_prevents_horizontal_overflow():
    source = (ROOT / "app" / "styles.py").read_text(encoding="utf-8")

    assert "overflow-x: hidden !important" in source
    assert 'div[data-testid="stHorizontalBlock"]' in source
    assert "flex-wrap: wrap !important" in source
    assert "flex: 1 1 100% !important" in source


def test_region_and_city_cards_render_in_row_order():
    region_source = (ROOT / "app" / "components" / "multi_pick.py").read_text(encoding="utf-8")
    city_source = (ROOT / "app" / "components" / "city_list.py").read_text(encoding="utf-8")

    assert "cols[idx % 3]" not in region_source
    assert "range(0, len(top_regions), 3)" in region_source
    assert "grid_cols[i % 2]" not in city_source
    assert "range(0, len(gosterilecek_sehirler), 2)" in city_source


def test_mobile_selection_controls_render_before_cards():
    region_source = (ROOT / "app" / "components" / "multi_pick.py").read_text(encoding="utf-8")
    survey_source = (ROOT / "app" / "components" / "survey.py").read_text(encoding="utf-8")

    region_checkbox = region_source.index("checked = st.checkbox")
    region_card = region_source.index('st.markdown(\n                    f"""\n                    <div class="{card_class}">')
    assert region_checkbox < region_card

    context_checkbox = survey_source.index("checked = st.checkbox")
    context_card = survey_source.index('st.markdown(\n                    f"""\n                    <div class="{card_class}">')
    assert context_checkbox < context_card


def test_transparency_expanders_use_grouped_preference_vector():
    photo_source = (ROOT / "app" / "components" / "photo_pair.py").read_text(encoding="utf-8")
    survey_source = (ROOT / "app" / "components" / "survey.py").read_text(encoding="utf-8")

    assert "_preference_vector_html" in photo_source
    assert "_preference_vector_html" in survey_source
    assert "_feature_bars_html" not in photo_source
    assert "_feature_bars_html" not in survey_source


def test_streamlit_material_icons_keep_icon_font():
    source = (ROOT / "app" / "styles.py").read_text(encoding="utf-8")

    assert 'data-testid="stIconMaterial"' in source
    assert "Material Symbols Rounded" in source
    assert 'font-feature-settings: "liga"' in source
