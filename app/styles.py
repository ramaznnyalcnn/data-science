"""Global CSS injected with ``st.markdown(CSS, unsafe_allow_html=True)``."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path


def _asset_data_uri(relative_path: str) -> str:
    path = Path(__file__).resolve().parent / relative_path
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


_HERO_IMAGE = _asset_data_uri("../photos/tur4_sol.jpg")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --paper: #f7f3ec;
    --linen: #eee6da;
    --surface: #fffdf8;
    --surface-soft: #fbf7ef;
    --ink: #171b22;
    --slate: #59616b;
    --muted: #7a807e;
    --border: #d9cec0;
    --primary: #164c63;
    --primary-ink: #0f3343;
    --accent: #c79355;
    --coral: #b85f49;
    --success: #587a5a;
    --warning: #b66b35;
    --danger: #b94b57;
    --text-primary: var(--ink);
    --text-muted: var(--slate);
    --bg-card: var(--surface);
    --bg-card-hover: #fffaf0;
    --cyan: var(--primary);
    --accent-light: var(--accent);
    --accent-glow: rgba(199, 147, 85, 0.18);
}

* {
    box-sizing: border-box;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    letter-spacing: 0 !important;
}

span[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", sans-serif !important;
    font-weight: normal !important;
    font-style: normal !important;
    font-size: 20px !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    overflow-wrap: normal !important;
    font-feature-settings: "liga" !important;
    -webkit-font-feature-settings: "liga" !important;
    -webkit-font-smoothing: antialiased !important;
}

html,
body {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden !important;
}

.stApp {
    background:
        linear-gradient(180deg, rgba(255,253,248,0.86), rgba(247,243,236,0.98)),
        var(--paper) !important;
    color: var(--ink) !important;
    max-width: 100%;
    overflow-x: hidden !important;
}

header[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton,
.stApp > header {
    background: var(--paper) !important;
    background-color: var(--paper) !important;
    box-shadow: none !important;
}

header[data-testid="stHeader"]::before,
header[data-testid="stHeader"]::after {
    background: transparent !important;
}

header[data-testid="stHeader"] button,
div[data-testid="stToolbar"] button,
.stDeployButton button {
    background: transparent !important;
    color: var(--slate) !important;
}

div[data-testid="stToolbar"] svg,
.stDeployButton svg {
    color: var(--slate) !important;
    fill: var(--slate) !important;
}

.main .block-container,
.block-container {
    max-width: 1240px !important;
    padding-top: 22px !important;
    padding-bottom: 34px !important;
    overflow-x: hidden !important;
}

body, p, span, li, td, th, label, div {
    color: var(--ink);
    font-size: 1rem;
    line-height: 1.55;
    overflow-wrap: anywhere;
}

h1, h2, h3, h4,
.hero-title,
.brand-name,
.reveal-city {
    color: var(--ink) !important;
    font-family: Fraunces, Georgia, serif !important;
    letter-spacing: 0 !important;
}

hr {
    border: 0;
    border-top: 1px solid var(--border) !important;
}

section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

.global-nav {
    min-height: 52px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    margin: -8px 0 20px;
}

.global-nav-minimal {
    justify-content: center;
}

.language-gate {
    min-height: min(62vh, 560px);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    background: var(--surface);
    padding: 34px 24px;
    margin: 16px 0 18px;
}

.language-gate-copy {
    max-width: 620px;
    text-align: center;
}

.language-gate-kicker {
    color: var(--primary) !important;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.language-gate h1 {
    color: var(--ink) !important;
    font-family: Fraunces, Georgia, serif !important;
    font-size: 42px;
    line-height: 1.08;
    margin: 0 0 12px;
}

.language-gate p {
    color: var(--slate) !important;
    font-size: 16px;
    line-height: 1.5;
    margin: 0 auto;
}

.brand-lockup {
    display: flex;
    align-items: center;
    gap: 11px;
}

.brand-mark {
    width: 22px;
    height: 22px;
    display: inline-block;
    background:
        linear-gradient(135deg, var(--primary) 0 50%, transparent 50%),
        linear-gradient(315deg, var(--accent) 0 50%, transparent 50%);
    border: 1px solid var(--ink);
}

.brand-name {
    font-size: 26px;
    font-weight: 700;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 22px;
    color: var(--slate);
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
}

.nav-links span {
    color: var(--slate);
    font-size: 12px;
}

.nav-lang {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 7px 13px;
    color: var(--primary) !important;
    background: var(--surface);
}

.app-footer {
    border-top: 1px solid var(--border);
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    padding: 22px 0 8px;
    margin-top: 42px;
    color: var(--slate);
    font-size: 13px;
}

.app-footer span {
    color: var(--slate);
    font-size: 13px;
}

.editorial-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(330px, 0.9fr);
    min-height: 250px;
    border: 1px solid var(--border);
    background: var(--surface);
    margin-bottom: 12px;
}

.hero-copy {
    padding: 26px 42px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.hero-title {
    font-size: 32px;
    line-height: 1.03;
    font-weight: 700;
    margin: 0 0 12px;
}

.hero-sub {
    max-width: 510px;
    color: var(--slate) !important;
    font-size: 15px;
    line-height: 1.42;
    margin: 0 0 12px;
}

.hero-note {
    color: var(--muted) !important;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.hero-photo {
    min-height: 250px;
    background-image:
        linear-gradient(180deg, rgba(23,27,34,0.04), rgba(23,27,34,0.20)),
        url("__HERO_IMAGE__");
    background-size: cover;
    background-position: center;
}

.control-panel,
.progress-rail,
.option-card,
.shortlist-card,
.gb-kart,
.oneri-kart,
.progress-box,
.glass-panel {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

.control-panel {
    display: grid;
    gap: 18px;
    padding: 24px;
    margin-top: 22px;
}

.tutorial-strip {
    margin: 10px 0 20px;
}

.tutorial-kicker {
    color: var(--primary) !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.tutorial-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 12px;
}

.tutorial-card {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 14px 16px;
    min-height: 118px;
}

.tutorial-mobile-card {
    display: none;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 13px 14px;
}

.tutorial-title {
    color: var(--ink) !important;
    font-size: 15px;
    font-weight: 800;
    line-height: 1.35;
    margin-bottom: 6px;
}

.tutorial-body {
    color: var(--slate) !important;
    font-size: 13px;
    line-height: 1.45;
}

.section-kicker,
.rail-kicker,
.question-meta,
.oneri-skor-label {
    color: var(--primary) !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    margin-top: 4px;
    margin-bottom: 2px;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.45rem !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: 1rem !important;
}

.flow-title,
.soru-baslik {
    text-align: center;
    padding: 22px 0 18px;
}

.flow-title h2,
.soru-baslik h2 {
    font-size: 36px;
    font-weight: 700;
    line-height: 1.13;
    margin: 0 0 8px;
    text-shadow: none !important;
}

.flow-title p,
.soru-baslik p {
    max-width: 720px;
    color: var(--slate) !important;
    font-size: 16px;
    line-height: 1.52;
    margin: 0 auto;
}

.question-meta {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 14px;
}

.progress-dots {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 18px;
}

.progress-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    border: 1px solid var(--stone, #b8b0a3);
    background: transparent;
}

.progress-dot.filled {
    background: var(--primary);
    border-color: var(--primary);
}

.progress-rail {
    position: sticky;
    top: 24px;
    padding: 20px;
    min-height: 352px;
    background: var(--linen) !important;
}

.rail-meta,
.rail-pool span {
    color: var(--slate);
    font-size: 13px;
}

.rail-steps {
    display: grid;
    gap: 14px;
    margin: 30px 0;
}

.rail-step {
    display: flex;
    gap: 10px;
    align-items: center;
    color: var(--muted);
}

.rail-step span,
.rail-step b {
    color: inherit;
    font-size: 14px;
}

.rail-step.done,
.rail-step.active {
    color: var(--primary);
}

.rail-pool {
    border-top: 1px solid var(--border);
    padding-top: 18px;
}

.rail-pool strong {
    display: block;
    color: var(--ink);
    font-family: Fraunces, Georgia, serif !important;
    font-size: 34px;
    line-height: 1;
}

.photo-caption {
    border: 1px solid var(--border) !important;
    border-top: 0 !important;
    border-radius: 0 0 8px 8px !important;
    padding: 15px 17px !important;
    background: var(--surface) !important;
    min-height: 78px;
    margin: 0 0 12px !important;
}

.photo-caption-title {
    color: var(--primary) !important;
    font-size: 12px !important;
    font-weight: 800;
    margin-bottom: 4px;
    text-transform: uppercase;
}

.photo-caption-text {
    color: var(--slate) !important;
    font-size: 14px;
    line-height: 1.38;
}

div[data-testid="stImage"] {
    border-radius: 8px 8px 0 0 !important;
    box-shadow: none !important;
    overflow: hidden;
}

div[data-testid="stImage"]:hover {
    transform: none !important;
    box-shadow: none !important;
}

div[data-testid="stImage"] img {
    border: 1px solid var(--border);
    border-radius: 8px 8px 0 0 !important;
    object-fit: cover;
}

.option-card {
    padding: 22px !important;
    min-height: 196px;
    transition: border-color 120ms ease, background 120ms ease;
}

.option-card:hover,
.shortlist-card:hover {
    border-color: var(--primary) !important;
    background: var(--bg-card-hover) !important;
}

.option-card.selected,
.shortlist-card.selected {
    border: 2px solid var(--primary) !important;
    background: #fff9ee !important;
}

.option-card-title {
    color: var(--ink) !important;
    font-size: 20px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 12px;
}

.option-card-desc {
    color: var(--slate) !important;
    font-size: 15px;
    line-height: 1.5;
    margin-bottom: 16px;
}

.option-card-meta {
    border-top: 1px solid var(--border);
    color: var(--primary) !important;
    font-size: 12px;
    font-weight: 800;
    padding-top: 12px;
    text-transform: uppercase;
}

.shortlist-card {
    padding: 18px;
    min-height: 168px;
    margin-bottom: 1rem;
}

.dot-rating {
    color: var(--accent);
    font-size: 14px;
    letter-spacing: 2px !important;
}

.progress-box {
    padding: 16px 18px;
    margin-bottom: 18px;
}

.progress-label {
    color: var(--slate);
    font-size: 13px;
    font-weight: 800;
}

.progress-bar-outer,
.feat-bar-outer {
    background: #e8ded1;
    border-radius: 999px;
    overflow: hidden;
}

.progress-bar-outer {
    height: 10px;
    margin-top: 8px;
}

.progress-bar-inner,
.feat-bar-inner {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--primary), var(--accent));
}

.progress-info,
.feat-row {
    display: flex;
    align-items: center;
    gap: 10px;
}

.progress-info {
    justify-content: space-between;
    margin-top: 8px;
}

.progress-info span,
.feat-name,
.feat-pct {
    color: var(--slate);
    font-size: 13px;
}

.feat-row {
    margin-bottom: 8px;
}

.feat-icon {
    color: var(--primary);
    width: 20px;
    text-align: center;
}

.feat-name {
    width: 112px;
    font-weight: 700;
}

.feat-bar-outer {
    flex: 1;
    height: 7px;
}

.feat-pct {
    width: 42px;
    text-align: right;
    font-weight: 800;
}

.vector-groups {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
}

.vector-group {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 14px 16px;
}

.vector-group-title {
    color: var(--ink) !important;
    font-size: 15px;
    font-weight: 800;
    line-height: 1.35;
    margin-bottom: 4px;
}

.vector-group-desc {
    color: var(--slate) !important;
    font-size: 13px;
    line-height: 1.4;
    margin-bottom: 12px;
}

.oneri-kart {
    padding: 20px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}

.oneri-kart::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--primary);
}

.oneri-kart.gold::before { background: var(--accent); }
.oneri-kart.silver::before { background: #8a98a7; }
.oneri-kart.bronze::before { background: var(--coral); }

.oneri-sehir {
    color: var(--ink);
    font-size: 1.55rem;
    font-weight: 800;
    margin: 0;
}

.oneri-tip {
    display: inline-block;
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--primary);
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 800;
    margin-top: 8px;
}

.oneri-skor {
    color: var(--primary);
    font-size: 2.3rem;
    font-weight: 900;
    text-align: right;
    line-height: 1;
}

.gb-kart {
    padding: 28px 24px;
    text-align: center;
}

.alert-success,
.alert-info {
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 16px;
    font-weight: 700;
}

.alert-success {
    background: #edf6ec;
    border: 1px solid #bdd4ba;
    color: var(--success);
}

.alert-info {
    background: #edf5f6;
    border: 1px solid #b9d5dc;
    color: var(--primary);
}

div[data-testid="stButton"] > button {
    min-height: 44px !important;
    border-radius: 999px !important;
    border: 1px solid var(--ink) !important;
    background: transparent !important;
    color: var(--ink) !important;
    font-size: 0.98rem !important;
    font-weight: 800 !important;
    box-shadow: none !important;
    transition: background 120ms ease, border-color 120ms ease, color 120ms ease, transform 120ms ease !important;
}

div[data-testid="stButton"] > button:hover {
    border-color: var(--primary) !important;
    color: var(--primary) !important;
    background: #eef5f4 !important;
    transform: translateY(-1px) !important;
}

div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: var(--ink) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {
    background: #d2a465 !important;
    border-color: #d2a465 !important;
    color: var(--ink) !important;
}

div[data-testid="stButton"] > button:disabled {
    opacity: 0.55 !important;
    transform: none !important;
}

label,
.stSelectbox label,
.stMultiSelect label,
.stRadio label,
.stCheckbox label {
    color: var(--slate) !important;
    font-weight: 700 !important;
}

.stSelectbox > div > div,
.stMultiSelect > div > div,
textarea,
input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
}

.stRadio > div {
    gap: 0.55rem;
}

.stRadio > div > label {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 999px !important;
    padding: 0.65rem 1rem !important;
    color: var(--ink) !important;
}

.stRadio > div > label:hover {
    border-color: var(--primary) !important;
    background: #ffffff !important;
}

label[data-baseweb="radio"] {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 999px !important;
    padding: 0.65rem 1rem !important;
    max-width: 100% !important;
}

label[data-baseweb="radio"]:hover {
    border-color: var(--primary) !important;
    background: #ffffff !important;
}

label[data-baseweb="radio"] > div:first-child {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
}

label[data-baseweb="radio"] > div:first-child > div {
    background: #ffffff !important;
}

label[data-baseweb="radio"]:has(input:checked) > div:first-child {
    border-color: var(--primary) !important;
}

label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
    background: var(--accent) !important;
}

label[data-baseweb="checkbox"] {
    background: transparent !important;
    max-width: 100% !important;
    margin: 0 0 0.35rem 0 !important;
    align-items: center !important;
}

label[data-baseweb="checkbox"] > span:first-child {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    color: var(--primary) !important;
}

label[data-baseweb="checkbox"]:has(input:checked) > span:first-child {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #ffffff !important;
    position: relative !important;
}

label[data-baseweb="checkbox"]:has(input:checked) > span:first-child::after {
    content: "✓" !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #ffffff !important;
    font-size: 13px !important;
    font-weight: 900 !important;
    line-height: 1 !important;
}

label[data-baseweb="checkbox"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
}

input[type="radio"],
input[type="checkbox"] {
    accent-color: var(--primary);
}

details[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    background: var(--surface) !important;
}

.streamlit-expanderHeader {
    color: var(--ink) !important;
    font-weight: 800 !important;
}

div[data-testid="stMarkdownContainer"] h3 {
    color: var(--ink) !important;
    font-size: 1.35rem !important;
    line-height: 1.38 !important;
}

@media (max-width: 900px) {
    .global-nav {
        align-items: flex-start;
        padding-bottom: 16px;
    }

    .nav-links {
        gap: 12px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .editorial-hero {
        grid-template-columns: 1fr;
        min-height: auto;
    }

    .hero-copy {
        padding: 22px 24px;
    }

    .hero-title {
        font-size: 28px;
    }

    .hero-sub {
        font-size: 16px;
    }

    .hero-photo {
        min-height: 170px;
    }

    .progress-rail {
        position: static;
        min-height: auto;
        margin-bottom: 20px;
    }
}

@media (max-width: 700px) {
    .main .block-container,
    .block-container {
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-top: 12px !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    .global-nav {
        margin-bottom: 14px;
    }

    .brand-name {
        font-size: 22px;
    }

    .nav-links span:not(.nav-lang) {
        display: none;
    }

    .language-gate {
        min-height: min(54vh, 460px);
        padding: 24px 18px;
        margin: 8px 0 14px;
    }

    .language-gate h1 {
        font-size: 30px;
    }

    .language-gate p {
        font-size: 14px;
    }

    .hero-copy {
        padding: 20px;
    }

    .hero-title {
        font-size: 26px;
    }

    .hero-photo {
        min-height: 130px;
    }

    .control-panel {
        padding: 16px;
    }

    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.75rem !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: 100% !important;
        flex: 1 1 100% !important;
    }

    .tutorial-grid {
        display: none;
    }

    .tutorial-mobile-card {
        display: block;
    }

    .tutorial-strip {
        margin: 8px 0 14px;
    }

    .flow-title h2,
    .soru-baslik h2 {
        font-size: 28px;
    }

    .flow-title p,
    .soru-baslik p {
        font-size: 15px;
    }

    .option-card {
        min-height: 150px;
        padding: 16px !important;
    }

    .option-card-title {
        font-size: 17px;
    }

    .vector-groups {
        grid-template-columns: 1fr;
    }

    div[data-testid="stButton"] > button {
        min-height: 46px !important;
        font-size: 0.95rem !important;
    }

    .oneri-sehir {
        font-size: 1.25rem;
    }

    .oneri-skor {
        font-size: 1.8rem;
    }
}
</style>
""".replace("__HERO_IMAGE__", _HERO_IMAGE)
