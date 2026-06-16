"""Shared helper functions and constants for app components."""

from __future__ import annotations

import csv
import html
import json
import os
from datetime import datetime

import numpy as np
import streamlit as st

from model.config import FEATURES, FIZIK_FEATURES, QUALITY_FEATURES, SOSYAL_FEATURES
from model.file_lock import exclusive_file_lock
from model.recommend import candidate_pool_for_regions
from app.lang import feat as _label_feature
from app.lang import t  # noqa: F401 — re-exported for convenience

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

FEATURE_TR = {
    "deniz": "Deniz", "doga": "Doga", "tarih": "Tarih", "kultur": "Kultur",
    "eglence": "Eglence", "sakin": "Sakin", "doga_spor": "Doga Sporu",
    "su_spor": "Su Sporu", "hava_spor": "Hava Sporu", "kis_spor": "Kis Sporu",
    "yemek": "Yemek", "ulasim_kolayligi": "Ulasim", "fiyat": "Butce",
    "safety": "Guvenlik", "pollution": "Temizlik",
    "livability": "Yasanabilirlik", "health_risk": "Saglik Riski",
}
FEATURE_ICON = {f: "•" for f in FEATURE_TR}
MADALYA = ["1.", "2.", "3."]

# ── Safety data (module-level load) ───────────────────────
_SAFETY_DATA: dict = {}
_SAFETY_JSON_PATH = os.path.join(DATA_DIR, "city_safety.json")
if os.path.exists(_SAFETY_JSON_PATH):
    with open(_SAFETY_JSON_PATH, "r", encoding="utf-8") as _sf:
        _raw_sd = json.load(_sf)
        _SAFETY_DATA = {k: v for k, v in _raw_sd.items() if k != "_meta"}


# ── Text helpers ───────────────────────────────────────────

def _foto_aciklama(foto_bilgi: dict, lang: str) -> str:
    if lang == "EN":
        return foto_bilgi.get("aciklama_en", foto_bilgi.get("aciklama", ""))
    return foto_bilgi.get("aciklama", "")


def _sehir_aciklama(aciklamalar: dict, sehir: str, lang: str) -> str:
    val = aciklamalar.get(sehir, "")
    if isinstance(val, dict):
        return val.get(lang, val.get("TR", ""))
    return val


def _region_title(region: dict) -> str:
    title = region.get("name") or region.get("id", "").replace("region_", "")
    replacements = {
        "Kiyilari": "Kıyıları", "Sahili": "Sahili", "Turkiye": "Türkiye",
        "Sehirleri": "Şehirleri", "Guney": "Güney", "Dogu": "Doğu",
        "Bati": "Batı", "Kuzey": "Kuzey",
        "Kafkasya Ve Ipek Yolu": "Kafkasya ve İpek Yolu",
        "Guneydogu": "Güneydoğu", "Asya": "Asya", "Avrupa": "Avrupa",
        "Ortadogu": "Ortadoğu", "Orta Dogu": "Orta Doğu",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    return title


def _region_summary(region: dict) -> str:
    rid = region.get("id", "").lower()
    title = (region.get("name") or "").lower()
    text = f"{rid} {title}"
    rules = [
        (("ege", "kiyi"), "Sahil · koy · sosyal"),
        (("akdeniz",), "Deniz · güneş · rahat"),
        (("karadeniz",), "Doğa · yayla · sakin"),
        (("tarihi", "kapadokya"), "Tarih · kültür · manzara"),
        (("sehir", "istanbul"), "Lezzet · kültür · tempo"),
        (("balkan",), "Yakın rota · şehir · tarih"),
        (("kafkas", "ipek"), "Doğa · tarih · keşif"),
        (("afrika", "tunus", "fas"), "Çöl · tarih · renk"),
        (("japon", "kore"), "Şehir · kültür · yemek"),
        (("singapur", "malezya"), "Modern · yemek · tropik"),
        (("latin",), "Renk · müzik · şehir"),
        (("guney_amerika", "peru"), "Dağ · doğa · macera"),
        (("asya", "vietnam", "tayland"), "Tropik · sokak · keşif"),
        (("karayip",), "Deniz · ada · dinlenme"),
        (("doga", "safari"), "Doğa · vahşi · açık alan"),
        (("orta_dogu", "urdun"), "Tarih · çöl · mimari"),
        (("avrupa", "italya", "yunan"), "Kültür · şehir · lezzet"),
        (("kuzey", "iskandinav"), "Doğa · sakin · serin"),
        (("kis", "winter"), "Kar · dağ · spor"),
    ]
    for keys, summary in rules:
        if any(key in text for key in keys):
            return summary
    return "Keşif · deneyim · rota"


def _oneri_aciklama(oneri: dict, lang: str) -> str:
    raw = oneri.get("aciklama_raw", oneri.get("aciklama", ""))
    if isinstance(raw, dict):
        text = raw.get(lang, raw.get("TR", ""))
    else:
        text = raw
    return _temiz_oneri_aciklama(text)


def _temiz_oneri_aciklama(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if "Metin sinyalleri:" in text:
        text = text.split("Metin sinyalleri:", 1)[0].strip()
    generic_prefixes = (
        "Dengeli ve karakterli bir durak",
        "Kiyi atmosferi",
        "Tarihi dokuya yaslanan bir rota",
    )
    for prefix in generic_prefixes:
        if text.startswith(prefix) and ";" in text:
            text = text.split(";", 1)[1].strip()
            break
    if text:
        text = text[0].upper() + text[1:]
    return text


def _html_escape(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _compact_html(markup: str) -> str:
    return "".join(line.strip() for line in markup.splitlines() if line.strip())


# ── HTML builders ──────────────────────────────────────────

def _user_profile_html(u_fiz: np.ndarray, u_sos: np.ndarray, lang: str) -> str:
    values = []
    for feature, value in zip(FIZIK_FEATURES, u_fiz):
        values.append((feature, float(value), "physical"))
    for feature, value in zip(SOSYAL_FEATURES, u_sos):
        values.append((feature, float(value), "social"))
    values.sort(key=lambda item: item[1], reverse=True)

    if not values or values[0][1] < 0.08:
        text = (
            "Profilin henüz netleşmedi; birkaç seçimden sonra burada seni sınıf sınıf tarif edeceğiz."
            if lang == "TR"
            else "Your profile is not clear yet; after a few choices, this section will describe your priorities."
        )
        return _compact_html(f"""
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:8px;
                    padding:1rem 1.15rem; margin:0.4rem 0 1.2rem">
            <div style="color:var(--ink); font-weight:800; font-size:1.05rem; margin-bottom:0.35rem">
                {_html_escape('Tercih profilin' if lang == 'TR' else 'Your preference profile')}
            </div>
            <div style="color:var(--slate); line-height:1.45">{_html_escape(text)}</div>
        </div>
        """)

    groups = [
        (
            "En değer verdiklerin" if lang == "TR" else "Highest priorities",
            "Bu özellikler öneri skorunda ana yönü belirliyor." if lang == "TR" else "These signals drive the main recommendation direction.",
            values[:3], "#10b981",
        ),
        (
            "İkincil planların" if lang == "TR" else "Secondary plans",
            "Olursa öneriyi güçlendirir, ama tek başına karar verdirmez." if lang == "TR" else "They strengthen a match without deciding it alone.",
            values[3:6], "#818cf8",
        ),
        (
            "Varlığı olmasa da olur" if lang == "TR" else "Nice, not essential",
            "Eksik olursa şehir hemen elenmez." if lang == "TR" else "A city is not eliminated if these are missing.",
            values[6:9], "#f59e0b",
        ),
        (
            "Sana daha uzak duranlar" if lang == "TR" else "Least aligned",
            "Şu anki cevaplarına göre en düşük öncelikli sinyaller." if lang == "TR" else "Lowest-priority signals based on your current answers.",
            values[9:], "#f43f5e",
        ),
    ]

    group_html = ""
    for title, desc, items, color in groups:
        chips = ""
        for feature, value, _kind in items:
            pct = int(round(value * 100))
            chips += (
                f'<span style="display:inline-flex; align-items:center; gap:0.35rem; '
                f'background:var(--surface-soft); border:1px solid var(--border); '
                f'border-radius:999px; padding:0.28rem 0.62rem; margin:0.18rem; '
                f'color:var(--ink); font-size:0.82rem;">'
                f'{_html_escape(FEATURE_TR.get(feature, feature))} '
                f'<b style="color:{color}; font-weight:800">{pct}%</b></span>'
            )
        if not chips:
            chips = (
                f'<span style="color:var(--slate); font-size:0.86rem">'
                f'{_html_escape("Belirgin sinyal yok" if lang == "TR" else "No clear signal")}</span>'
            )
        group_html += f"""
        <div style="background:var(--surface); border:1px solid var(--border); border-left:4px solid {color};
                    border-radius:8px; padding:0.9rem 1rem; min-height:138px">
            <div style="color:var(--ink); font-weight:800; margin-bottom:0.25rem">{_html_escape(title)}</div>
            <div style="color:var(--slate); font-size:0.86rem; line-height:1.35; margin-bottom:0.55rem">
                {_html_escape(desc)}
            </div>
            <div>{chips}</div>
        </div>
        """

    intro = (
        "Vektörüne göre seni böyle okuyoruz; seçimler değiştikçe bu profil de güncellenir."
        if lang == "TR"
        else "This is how your vector currently reads; it updates as your choices change."
    )
    return _compact_html(f"""
    <div style="margin:0.2rem 0 1.4rem">
        <div style="color:var(--ink); font-weight:800; font-size:1.22rem; margin-bottom:0.25rem">
            {_html_escape('Tercih profilin' if lang == 'TR' else 'Your preference profile')}
        </div>
        <div style="color:var(--slate); font-size:0.98rem; line-height:1.45; margin-bottom:0.85rem">
            {_html_escape(intro)}
        </div>
        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:0.85rem">
            {group_html}
        </div>
    </div>
    """)


def _safety_badge_html(sehir: str) -> str:
    d = _SAFETY_DATA.get(sehir)
    if not d:
        return ""

    def _bar(val: float, color: str) -> str:
        pct = int(val * 100)
        return (
            f'<div style="flex:1; background:rgba(255,255,255,0.07); border-radius:999px; '
            f'height:5px; overflow:hidden;">'
            f'<div style="width:{pct}%; height:100%; background:{color}; border-radius:999px;"></div>'
            f'</div>'
        )

    safety_color    = "#10b981" if d["safety"]    >= 0.70 else ("#f59e0b" if d["safety"]    >= 0.50 else "#f43f5e")
    pollution_color = "#10b981" if d["pollution"]  >= 0.70 else ("#f59e0b" if d["pollution"]  >= 0.50 else "#f43f5e")
    live_color      = "#10b981" if d["livability"] >= 0.70 else ("#f59e0b" if d["livability"] >= 0.50 else "#f43f5e")

    warnings = []
    if d["pollution"] < 0.45:
        warnings.append('<span style="background:#f43f5e20; border:1px solid #f43f5e50; color:#fca5a5; '
                        'border-radius:6px; padding:0.15rem 0.6rem; font-size:0.75rem; font-weight:600;">'
                        'Hava kirliliği yüksek</span>')
    if d["safety"] < 0.50:
        warnings.append('<span style="background:#f59e0b20; border:1px solid #f59e0b50; color:#fcd34d; '
                        'border-radius:6px; padding:0.15rem 0.6rem; font-size:0.75rem; font-weight:600;">'
                        'Güvenlik düşük</span>')
    if d["health_risk"] < 0.50:
        warnings.append('<span style="background:#f43f5e20; border:1px solid #f43f5e50; color:#fca5a5; '
                        'border-radius:6px; padding:0.15rem 0.6rem; font-size:0.75rem; font-weight:600;">'
                        'Sağlık riski</span>')

    warn_html = (
        f'<div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.7rem">{" ".join(warnings)}</div>'
        if warnings else ""
    )

    return _compact_html(f"""
    <div style="margin-top:1rem; padding-top:0.8rem; border-top:1px solid var(--border);">
      <div style="display:grid; grid-template-columns:70px 1fr 32px; align-items:center;
                  gap:0.4rem 0.6rem; font-size:0.78rem;">
        <span style="color:var(--text-muted);">Güvenlik</span>
        {_bar(d['safety'], safety_color)}
        <span style="color:{safety_color}; font-weight:700; text-align:right;">{int(d['safety']*100)}%</span>
        <span style="color:var(--text-muted);">Temizlik</span>
        {_bar(d['pollution'], pollution_color)}
        <span style="color:{pollution_color}; font-weight:700; text-align:right;">{int(d['pollution']*100)}%</span>
        <span style="color:var(--text-muted);">Yaşanabilirlik</span>
        {_bar(d['livability'], live_color)}
        <span style="color:{live_color}; font-weight:700; text-align:right;">{int(d['livability']*100)}%</span>
      </div>
      {warn_html}
    </div>
    """)


def _oneri_kart_html(oneri: dict, rank: int) -> str:
    sinif = ["gold", "silver", "bronze"][rank] if rank < 3 else ""
    skor_pct = int(min(oneri["skor"] * 100, 100))
    madalya = MADALYA[rank] if rank < 3 else ""
    tip = oneri.get("tip", "")
    sehir = oneri["sehir"]
    safety_html = _safety_badge_html(sehir)
    return f"""
    <div class="oneri-kart {sinif}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start">
            <div>
                <div class="oneri-sehir">{madalya} {sehir}</div>
                <div class="oneri-tip">{tip}</div>
            </div>
            <div>
                <div class="oneri-skor">{skor_pct}%</div>
                <div class="oneri-skor-label">Uyum Skoru</div>
            </div>
        </div>
        {safety_html}
    </div>
    """


def _feature_bars_html(vektor, n: int = 6) -> str:
    result = ""
    for i, feat in enumerate(FEATURES[:n]):
        deger = float(vektor[i]) if vektor is not None else 0.0
        pct = int(deger * 100)
        result += f"""<div class="feat-row">
            <span class="feat-icon">{FEATURE_ICON.get(feat, '•')}</span>
            <span class="feat-name">{FEATURE_TR.get(feat, feat)}</span>
            <div class="feat-bar-outer">
                <div class="feat-bar-inner" style="width:{pct}%"></div>
            </div>
            <span class="feat-pct">{pct}%</span>
        </div>"""
    return result


def _preference_vector_html(u_fiz: np.ndarray, u_sos: np.ndarray, lang: str = "TR") -> str:
    """Render user preference vectors as physical and social groups."""

    def _rows(features: list[str], values: np.ndarray) -> str:
        rows = ""
        safe_values = np.asarray(values if values is not None else [], dtype=float)
        for idx, feature in enumerate(features):
            value = float(safe_values[idx]) if idx < len(safe_values) else 0.0
            value = max(0.0, min(1.0, value))
            pct = int(round(value * 100))
            rows += f"""
            <div class="feat-row">
                <span class="feat-icon">{FEATURE_ICON.get(feature, '•')}</span>
                <span class="feat-name">{_html_escape(_label_feature(feature, lang))}</span>
                <div class="feat-bar-outer">
                    <div class="feat-bar-inner" style="width:{pct}%"></div>
                </div>
                <span class="feat-pct">{pct}%</span>
            </div>
            """
        return rows

    fiz_title = "Rota / görsel tercihler" if lang == "TR" else "Route / visual preferences"
    sos_title = "Sosyal / pratik tercihler" if lang == "TR" else "Social / practical preferences"
    fiz_desc = (
        "Fotoğraf ve rota seçimlerinden çıkarılan gözlenebilir seyahat sinyalleri."
        if lang == "TR"
        else "Observable travel signals inferred from photo and route choices."
    )
    sos_desc = (
        "Tempo, yemek, ulaşım ve bütçe gibi günlük deneyim sinyalleri."
        if lang == "TR"
        else "Everyday experience signals such as pace, food, transport, and budget."
    )

    return _compact_html(f"""
    <div class="vector-groups">
        <div class="vector-group">
            <div class="vector-group-title">{_html_escape(fiz_title)}</div>
            <div class="vector-group-desc">{_html_escape(fiz_desc)}</div>
            {_rows(FIZIK_FEATURES, u_fiz)}
        </div>
        <div class="vector-group">
            <div class="vector-group-title">{_html_escape(sos_title)}</div>
            <div class="vector-group-desc">{_html_escape(sos_desc)}</div>
            {_rows(SOSYAL_FEATURES, u_sos)}
        </div>
    </div>
    """)


def _progress_html(pct: float, soru: int, toplam: int, kalan_min: int, lang: str = "TR") -> str:
    bar_width = int(min(pct * 100, 100))
    if bar_width >= 100:
        durum = "✅ Enough data — heading to results..." if lang == "EN" else "✅ Yeterli veri toplandı, sonuca gidiliyor..."
    else:
        durum = (f'At least <b style="color:#a5b4fc">{kalan_min}</b> more questions before results'
                 if lang == "EN"
                 else f'En az <b style="color:#a5b4fc">{kalan_min}</b> soru daha sonra sonuca ulaşacağız')
    conf_label = t("confidence_label", lang)
    q_label    = t("question_label", lang)
    mx_label   = t("max_label", lang)
    return f"""
    <div class="progress-box">
        <div class="progress-label">{conf_label}</div>
        <div class="progress-bar-outer">
            <div class="progress-bar-inner" style="width:{bar_width}%"></div>
        </div>
        <div class="progress-info">
            <span>{q_label} <b style="color:var(--ink)">{soru}</b> / {mx_label} {toplam}</span>
            <span class="pct">{bar_width}%</span>
        </div>
        <div style="margin-top:0.6rem; color:var(--slate); font-size:0.82rem">{durum}</div>
    </div>
    """


def _alt_ilerleme_goster(adim: str, lang: str) -> None:
    siralar = {
        "giris": 0, "fotograf": 1, "region_pick": 2,
        "context": 3, "anket_static": 3, "free_text_vibe": 3,
        "anket_adaptive": 3, "anket_v2": 3, "oneri": 4, "geri_bildirim": 4,
    }
    aktif = siralar.get(adim, 0)
    etiketler = (
        ["Başlangıç", "Resim Seçme", "Bölge Seçme", "Anket Doldurma", "Şehir Seçme"]
        if lang == "TR"
        else ["Start", "Choose Images", "Choose Region", "Survey", "Choose Cities"]
    )
    st.divider()
    cols = st.columns(5)
    for i, (col, etiket) in enumerate(zip(cols, etiketler)):
        metin = f"{i + 1}. {etiket}" if i >= aktif else etiket
        with col:
            if i == aktif:
                st.markdown(f"**{metin}**")
            else:
                st.caption(metin)


# ── State / data helpers ───────────────────────────────────

def _kaydet(kullanici_v, sehir: str, begendi: int) -> None:
    yol = os.path.join(DATA_DIR, "kullanici_veri.csv")
    simdi = datetime.now()
    satir = list(kullanici_v) + [sehir, begendi, simdi.isoformat()]
    header = FEATURES + ["oneri_sehir", "begendi", "zaman"]

    with exclusive_file_lock(yol):
        if os.path.exists(yol) and os.path.getsize(yol) > 0:
            try:
                with open(yol, "r", newline="") as f:
                    rows = list(csv.reader(f))
                if rows and rows[0] != header:
                    old_header = rows[0]
                    migrated = [header]
                    for old_row in rows[1:]:
                        old_map = {name: old_row[idx] for idx, name in enumerate(old_header) if idx < len(old_row)}
                        new_row = []
                        for feature in FEATURES:
                            if feature in old_map:
                                new_row.append(old_map[feature])
                            elif feature in QUALITY_FEATURES:
                                new_row.append("0.5")
                            else:
                                new_row.append("0.0")
                        new_row.extend([
                            old_map.get("oneri_sehir", ""),
                            old_map.get("begendi", ""),
                            old_map.get("zaman", ""),
                        ])
                        migrated.append(new_row)
                    with open(yol, "w", newline="") as f:
                        csv.writer(f).writerows(migrated)
            except Exception:
                pass

        if os.path.exists(yol) and os.path.getsize(yol) > 0:
            try:
                with open(yol, "r", newline="") as f:
                    son_satirlar = list(csv.reader(f))
                if son_satirlar:
                    son = son_satirlar[-1]
                    if len(son) >= len(satir):
                        ayni_payload = son[:-1] == [str(x) for x in satir[:-1]]
                        if ayni_payload:
                            try:
                                son_zaman = datetime.fromisoformat(son[-1])
                                if (simdi - son_zaman).total_seconds() < 5:
                                    return
                            except (ValueError, IndexError):
                                pass
            except Exception:
                pass

        with open(yol, "a", newline="") as f:
            writer = csv.writer(f)
            if not os.path.exists(yol) or os.path.getsize(yol) == 0:
                writer.writerow(header)
            writer.writerow(satir)


def _yeniden_baslat() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def _reset_city_stage_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("chk_"):
            del st.session_state[key]
    if "stage2_shown_order" in st.session_state:
        del st.session_state["stage2_shown_order"]
    if "stage2_ranked_key" in st.session_state:
        del st.session_state["stage2_ranked_key"]
    st.session_state.stage2_feedback = None
    st.session_state.stage2_feedback_comment = ""


def _filter_regions_safe(df, region_ids, user_sosyal_v=None, sort_by_social=False):
    try:
        out = candidate_pool_for_regions(df, region_ids, user_sosyal_v, sort_by_social=sort_by_social)
    except TypeError:
        from model.region_ranker import filter_by_regions as _filter_by_regions
        out = _filter_by_regions(df, region_ids)
        if sort_by_social and user_sosyal_v is not None and out is not None and not out.empty:
            scores = []
            for _, row in out.iterrows():
                city_sos = row[SOSYAL_FEATURES].values.astype(float)
                norm_a = float(np.linalg.norm(user_sosyal_v))
                norm_b = float(np.linalg.norm(city_sos))
                score = 0.0 if norm_a == 0.0 or norm_b == 0.0 else float(np.dot(user_sosyal_v, city_sos) / (norm_a * norm_b))
                scores.append(score)
            out = out.copy()
            out["_social_match"] = scores
            out = out.sort_values("_social_match", ascending=False).drop(columns=["_social_match"])
    return out.reset_index(drop=True)


def _region_pick_commit(region_ids, shown_region_ids, none_fallback_count=0) -> None:
    base_df = st.session_state.scope_filtered_df
    if base_df is None or base_df.empty:
        base_df = st.session_state.filtered_df
    if base_df is None or base_df.empty:
        base_df = st.session_state.df

    city_df = _filter_regions_safe(
        base_df, list(region_ids), st.session_state.kullanici_sosyal_v, sort_by_social=True,
    )
    if city_df.empty and region_ids:
        city_df = _filter_regions_safe(
            base_df, [], st.session_state.kullanici_sosyal_v, sort_by_social=True,
        )
    if city_df.empty:
        city_df = base_df.copy()

    st.session_state.selected_region_ids = list(region_ids)
    st.session_state.filtered_df = city_df
    st.session_state.oneriler = []
    st.session_state.reveal = False
    st.session_state.show_all_cities = False
    _reset_city_stage_state()

    sl = st.session_state.get("session_logger")
    if sl is not None:
        try:
            sl.log_region_pick(
                shown_top3=list(shown_region_ids),
                picked=list(region_ids),
                none_fallback_count=int(none_fallback_count),
            )
        except Exception as exc:
            print(f"[LOG] region_pick hata: {exc}")

    st.session_state.adim = "context"


def _show_all_regions() -> None:
    st.session_state.show_all_regions = True


def _show_recommended_regions() -> None:
    st.session_state.show_all_regions = False
