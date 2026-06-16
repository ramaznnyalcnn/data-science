"""Guardrails for tutorial copy shown in the Streamlit flow."""

from __future__ import annotations

from app.components.tutorial import (
    MOBILE_TUTORIAL_COPY,
    TUTORIAL_COPY,
    get_mobile_tutorial_summary,
    get_tutorial_cards,
)


EXPECTED_STAGES = {
    "giris",
    "fotograf",
    "region_pick",
    "context",
    "anket_adaptive",
    "geri_bildirim",
}


def test_tutorial_copy_exists_for_tr_and_en():
    assert EXPECTED_STAGES <= set(TUTORIAL_COPY)

    for stage in EXPECTED_STAGES:
        assert set(TUTORIAL_COPY[stage]) == {"TR", "EN"}
        for lang in ("TR", "EN"):
            cards = get_tutorial_cards(stage, lang)
            assert cards
            for title, body in cards:
                assert title.strip()
                assert body.strip()


def test_intro_copy_explains_scope_and_visa():
    tr_body = " ".join(body for _, body in get_tutorial_cards("giris", "TR")).lower()
    en_body = " ".join(body for _, body in get_tutorial_cards("giris", "EN")).lower()

    assert "türkiye" in tr_body
    assert "vize" in tr_body
    assert "visa" in en_body
    assert "world" in en_body


def test_results_copy_explains_anonymity_and_bias():
    tr_body = " ".join(body for _, body in get_tutorial_cards("geri_bildirim", "TR")).lower()
    en_body = " ".join(body for _, body in get_tutorial_cards("geri_bildirim", "EN")).lower()

    assert "gizli" in tr_body
    assert "meşhur" in tr_body
    assert "hidden" in en_body
    assert "bias" in en_body


def test_stage_aliases_share_existing_copy():
    assert get_tutorial_cards("anket_static", "TR") == get_tutorial_cards("anket_adaptive", "TR")
    assert get_tutorial_cards("oneri", "EN") == get_tutorial_cards("geri_bildirim", "EN")


def test_mobile_tutorial_copy_exists_for_tr_and_en():
    assert EXPECTED_STAGES <= set(MOBILE_TUTORIAL_COPY)

    for stage in EXPECTED_STAGES:
        assert set(MOBILE_TUTORIAL_COPY[stage]) == {"TR", "EN"}
        for lang in ("TR", "EN"):
            summary = get_mobile_tutorial_summary(stage, lang)
            assert summary is not None
            title, body = summary
            assert title.strip()
            assert body.strip()
