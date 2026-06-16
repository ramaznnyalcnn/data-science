"""Inline tutorial cards for the recommendation flow."""

from __future__ import annotations

import html
from typing import Final

import streamlit as st

TutorialCard = tuple[str, str]
TutorialSummary = tuple[str, str]

TUTORIAL_COPY: Final[dict[str, dict[str, list[TutorialCard]]]] = {
    "giris": {
        "TR": [
            (
                "Bu site ne yapar?",
                "Popüler listeleri tekrar etmez; kısa bir testle senin gezi hissine yakın şehirleri bulmaya çalışır.",
            ),
            (
                "Vize neden soruluyor?",
                "Türkiye seçersen vize filtresi gerekmez. Dünya veya TR + Dünya seçersen, vizesiz ya da vizeli dahil havuzu sen belirlersin.",
            ),
            (
                "İsimleri neden gizliyoruz?",
                "Meşhur şehir adı etkisini azaltmak için önce sadece açıklamaları gösteririz; böylece sana gerçekten yakın yerleri seçersin.",
            ),
        ],
        "EN": [
            (
                "What does this site do?",
                "It does not repeat popular lists; it uses a short test to find places close to your travel feel.",
            ),
            (
                "Why ask about visas?",
                "If you choose Turkey, no visa filter is needed. If you choose World or TR + World, you decide whether to keep only visa-free places or include visa-required ones.",
            ),
            (
                "Why hide city names?",
                "We first show descriptions without famous names to reduce popularity bias, then reveal the places you selected.",
            ),
        ],
    },
    "fotograf": {
        "TR": [
            (
                "Doğru cevap yok",
                "İki görselden hangisi seni daha çok çekiyorsa onu seç. İlk hissin model için yeterli sinyal verir.",
            ),
            (
                "Neyi öğreniyoruz?",
                "Fotoğraflar deniz, doğa, tarih, tempo ve spor gibi tercihlerini yavaş yavaş çıkarır.",
            ),
        ],
        "EN": [
            (
                "There is no right answer",
                "Pick the image that pulls you more. Your first instinct is enough signal for the model.",
            ),
            (
                "What are we learning?",
                "Photos gradually reveal preferences like coast, nature, history, pace, and activity.",
            ),
        ],
    },
    "region_pick": {
        "TR": [
            (
                "Önce rota grubu",
                "Bu adımda tek şehir seçmiyorsun; aramayı sana yakın birkaç rota grubuna daraltıyoruz.",
            ),
            (
                "Filtreler korunur",
                "Başta seçtiğin Türkiye, Dünya ve vize tercihleri bu bölge önerilerinde de geçerli kalır.",
            ),
        ],
        "EN": [
            (
                "Route group first",
                "You are not choosing one city yet; this narrows the search to route groups that fit you.",
            ),
            (
                "Filters stay active",
                "Your Turkey, World, and visa choices still apply to these region suggestions.",
            ),
        ],
    },
    "context": {
        "TR": [
            (
                "NLP burada ne yapıyor?",
                "Kendi cümleni yazarsan NLP şehir adı aramak yerine tatil hissini, örneğin sakin sahil veya iyi yemek gibi sinyallere çevirir.",
            ),
            (
                "Şehir adı yazman gerekmez",
                "İstersen sadece kart seç. İstersen hislerini yaz. İkisi birlikte daha net profil oluşturur.",
            ),
        ],
        "EN": [
            (
                "What does NLP do here?",
                "If you write a sentence, NLP turns travel feel into signals like calm coast or good food instead of searching for a city name.",
            ),
            (
                "You do not need a city name",
                "Pick cards, write your own mood, or use both. Together they make the profile clearer.",
            ),
        ],
    },
    "anket_adaptive": {
        "TR": [
            (
                "Son netleştirme",
                "Bu sorular fotoğraf ve metinden hâlâ belirsiz kalan tercihleri tamamlar.",
            ),
            (
                "Uymuyorsa geç",
                "İki seçenek de seni anlatmıyorsa soruyu geçebilirsin; sistem bunu zayıf sinyal olarak ele alır.",
            ),
        ],
        "EN": [
            (
                "Final refinement",
                "These questions fill in preferences that are still unclear after photos and text.",
            ),
            (
                "Skip if neither fits",
                "If neither option describes you, skip the question; the system treats that as a weak signal.",
            ),
        ],
    },
    "geri_bildirim": {
        "TR": [
            (
                "Önce açıklamaya bak",
                "Şehir isimleri ilk anda gizli kalır; seçimi açıklama, rota hissi ve uyum işaretlerine göre yap.",
            ),
            (
                "Bias etkisini azaltıyoruz",
                "Amaç, sadece meşhur olduğu veya herkes konuşuyor diye bir yeri seçmeni engelleyip sana yakın olabilecek şehirleri bulmak.",
            ),
            (
                "Sonra isimler açılır",
                "Beğendiğin seçenekleri kaydedince seçtiğin şehir adları görünür ve geri bildirimin modele yazılır.",
            ),
        ],
        "EN": [
            (
                "Read the description first",
                "City names stay hidden at first; choose by description, route feel, and match signals.",
            ),
            (
                "Reducing bias",
                "The goal is to reduce popularity bias, avoid picking a place only because everyone knows it, and focus on cities that may actually fit you.",
            ),
            (
                "Then names are revealed",
                "When you save your picks, selected city names appear and your feedback is logged.",
            ),
        ],
    },
}

STAGE_ALIASES: Final[dict[str, str]] = {
    "anket_static": "anket_adaptive",
    "oneri": "geri_bildirim",
}

MOBILE_TUTORIAL_COPY: Final[dict[str, dict[str, TutorialSummary]]] = {
    "giris": {
        "TR": (
            "Kısa rehber",
            "Önce rota havuzunu ve gerekiyorsa vize tercihini seç; şehir adları sonradan açılır ki meşhur isim etkisi azalsın.",
        ),
        "EN": (
            "Quick guide",
            "Choose the route pool and visa preference first; city names are revealed later to reduce popularity bias.",
        ),
    },
    "fotograf": {
        "TR": (
            "İlk hissini seç",
            "Doğru cevap yok. İki görselden hangisi seni çekiyorsa onu seç; bu tercih profilini şekillendirir.",
        ),
        "EN": (
            "Pick your first instinct",
            "There is no right answer. Choose the image that pulls you more; it shapes your profile.",
        ),
    },
    "region_pick": {
        "TR": (
            "Rota grubunu daralt",
            "Henüz tek şehir seçmiyorsun. Sana yakın gelen bölge gruplarını kısa listeye ekle.",
        ),
        "EN": (
            "Narrow the route group",
            "You are not choosing one city yet. Add the region groups that feel closest.",
        ),
    },
    "context": {
        "TR": (
            "Hissini anlat",
            "Kart seçebilir veya kısa cümle yazabilirsin; NLP bunu şehir adı yerine tatil sinyaline çevirir.",
        ),
        "EN": (
            "Describe the feel",
            "Pick cards or write a short sentence; NLP turns it into travel signals, not a city search.",
        ),
    },
    "anket_adaptive": {
        "TR": (
            "Son netleştirme",
            "Sana daha yakın seçeneği işaretle. İkisi de uymuyorsa soruyu geçebilirsin.",
        ),
        "EN": (
            "Final refinement",
            "Choose the closer option. If neither fits, you can skip the question.",
        ),
    },
    "geri_bildirim": {
        "TR": (
            "Açıklamaya göre seç",
            "Önce şehir adları gizli kalır. Beğendiğin seçenekleri kaydedince isimler açılır.",
        ),
        "EN": (
            "Choose by description",
            "City names stay hidden first. Save the options you like to reveal the names.",
        ),
    },
}


def get_tutorial_cards(stage: str, lang: str = "TR") -> list[TutorialCard]:
    """Return tutorial cards for a stage with a safe language fallback."""
    canonical_stage = STAGE_ALIASES.get(stage, stage)
    stage_copy = TUTORIAL_COPY.get(canonical_stage, {})
    return list(stage_copy.get(lang) or stage_copy.get("TR") or [])


def get_mobile_tutorial_summary(stage: str, lang: str = "TR") -> TutorialSummary | None:
    """Return compact mobile tutorial text for a stage."""
    canonical_stage = STAGE_ALIASES.get(stage, stage)
    stage_copy = MOBILE_TUTORIAL_COPY.get(canonical_stage, {})
    return stage_copy.get(lang) or stage_copy.get("TR")


def render_tutorial(stage: str, lang: str | None = None) -> None:
    """Render compact tutorial cards for the active flow stage."""
    active_lang = lang or st.session_state.get("lang", "TR")
    cards = get_tutorial_cards(stage, active_lang)
    mobile_summary = get_mobile_tutorial_summary(stage, active_lang)
    if not cards and mobile_summary is None:
        return

    label = "Kısa rehber" if active_lang == "TR" else "Quick guide"
    card_html = "".join(
        (
            '<article class="tutorial-card">'
            f'<div class="tutorial-title">{html.escape(title)}</div>'
            f'<div class="tutorial-body">{html.escape(body)}</div>'
            "</article>"
        )
        for title, body in cards
    )
    mobile_html = ""
    if mobile_summary is not None:
        mobile_title, mobile_body = mobile_summary
        mobile_html = (
            '<div class="tutorial-mobile-card">'
            f'<div class="tutorial-title">{html.escape(mobile_title)}</div>'
            f'<div class="tutorial-body">{html.escape(mobile_body)}</div>'
            "</div>"
        )
    st.markdown(
        (
            f'<section class="tutorial-strip" aria-label="{html.escape(label)}">'
            f'<div class="tutorial-kicker">{html.escape(label)}</div>'
            f"{mobile_html}"
            f'<div class="tutorial-grid">{card_html}</div>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )
