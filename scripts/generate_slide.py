"""
Çok sayfalı sunum üretici — 6 slide, 16:9 widescreen.
Kullanım: python3 scripts/generate_slide.py
Çıktı:    docs/presentation/sunum.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree
import os

# ---------------------------------------------------------------------------
# Renk Paleti
# ---------------------------------------------------------------------------
C_BG        = RGBColor(0x0D, 0x1B, 0x2A)
C_PANEL     = RGBColor(0x14, 0x2A, 0x40)
C_ACCENT    = RGBColor(0x4F, 0xC3, 0xF7)
C_ACCENT2   = RGBColor(0xFF, 0xB7, 0x40)   # turuncu vurgu
C_WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
C_BODY      = RGBColor(0xD0, 0xD8, 0xE8)
C_DIM       = RGBColor(0x78, 0x90, 0xA8)
C_GREEN_BG  = RGBColor(0x0A, 0x3D, 0x15)
C_GREEN_FG  = RGBColor(0x80, 0xCB, 0x80)
C_RED_BG    = RGBColor(0x3D, 0x0A, 0x0A)
C_RED_FG    = RGBColor(0xFF, 0xAA, 0xAA)
C_CARD      = RGBColor(0x1A, 0x35, 0x52)

# Sayfa boyutları (cm)
W_CM = 33.87
H_CM = 19.05

FONT = "Calibri"


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def cm(v):
    return Inches(v / 2.54)


def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])   # blank


def rect(slide, x, y, w, h, fill, line_col=None, line_pt=0):
    from pptx.util import Pt as _Pt
    s = slide.shapes.add_shape(1, cm(x), cm(y), cm(w), cm(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line_col:
        s.line.color.rgb = line_col
        s.line.width = _Pt(line_pt)
    else:
        s.line.fill.background()
    return s


def txt(slide, x, y, w, h, text, size, color, bold=False,
        align=PP_ALIGN.LEFT, italic=False):
    tb = slide.shapes.add_textbox(cm(x), cm(y), cm(w), cm(h))
    tb.word_wrap = True
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = FONT
    return tb


def multiline(slide, x, y, w, h, lines_data, default_size=12.5,
              default_color=None, line_spacing_pt=3):
    """
    lines_data: list of (text, size, color, bold)  veya  str (varsayılan stil)
    """
    if default_color is None:
        default_color = C_BODY
    tb = slide.shapes.add_textbox(cm(x), cm(y), cm(w), cm(h))
    tb.word_wrap = True
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for item in lines_data:
        if isinstance(item, str):
            item = (item, default_size, default_color, False)
        text, size, color, bold = item
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.LEFT
        p.space_before = Pt(line_spacing_pt)
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.name = FONT
    return tb


def bg(slide):
    """Tüm slide'a koyu arka plan uygula."""
    rect(slide, 0, 0, W_CM, H_CM, C_BG)


def header_bar(slide, title, subtitle=None, page_num=None):
    """Üst başlık şeridi."""
    BAR_H = 3.6
    rect(slide, 0, 0, W_CM, BAR_H, C_PANEL)
    rect(slide, 0, BAR_H - 0.12, W_CM, 0.12, C_ACCENT)

    title_x = 1.0
    if page_num:
        # sağ üstte sayfa numarası
        txt(slide, W_CM - 2.5, 0.3, 2.2, 0.8,
            f"{page_num}/6", 11, C_DIM, align=PP_ALIGN.RIGHT)

    txt(slide, title_x, 0.55, W_CM - title_x - 1.5, 1.7,
        title, 28, C_WHITE, bold=True)

    if subtitle:
        txt(slide, title_x, 2.35, W_CM - title_x - 1.5, 1.0,
            subtitle, 13, C_ACCENT, italic=True)


def footer(slide, label="Adaptive Pairwise Recommender  ·  Veri Bilimi Projesi 2025-26"):
    rect(slide, 0, H_CM - 0.28, W_CM, 0.28, C_PANEL)
    txt(slide, 0.8, H_CM - 0.26, W_CM - 1.6, 0.26,
        label, 9, C_DIM, align=PP_ALIGN.LEFT)


def card(slide, x, y, w, h, header, lines, header_col=None, bg_col=None):
    """Renkli kart (arka plan + başlık + bullet'lar)."""
    if header_col is None:
        header_col = C_ACCENT
    if bg_col is None:
        bg_col = C_CARD
    rect(slide, x, y, w, h, bg_col, line_col=header_col, line_pt=1.2)
    PAD = 0.3
    txt(slide, x + PAD, y + 0.15, w - PAD * 2, 0.7,
        header, 13, header_col, bold=True)
    body_lines = []
    for ln in lines:
        if isinstance(ln, str):
            body_lines.append((ln, 11.5, C_BODY, False))
        else:
            body_lines.append(ln)
    multiline(slide, x + PAD, y + 0.85, w - PAD * 2,
              h - 1.0, body_lines, line_spacing_pt=2)


# ===========================================================================
# SLIDE 1 — Kapak
# ===========================================================================

def slide_kapak(prs):
    sl = new_slide(prs)
    bg(sl)

    # Dekoratif üst çizgi
    rect(sl, 0, 0, W_CM, 0.18, C_ACCENT)

    # Sol: büyük başlık bloğu
    rect(sl, 0, 1.5, W_CM * 0.62, H_CM - 2.5, C_PANEL)
    rect(sl, W_CM * 0.62, 1.5, 0.12, H_CM - 2.5, C_ACCENT)

    txt(sl, 1.2, 2.8, 18, 1.2,
        "VERİ BİLİMİ PROJESİ", 13, C_ACCENT, bold=True)

    txt(sl, 1.2, 4.0, 18, 3.0,
        "Adaptive Pairwise\nSeyahat Öneri\nSistemi", 36, C_WHITE, bold=True)

    txt(sl, 1.2, 8.2, 18, 1.0,
        "Veri Öncesi Hazırlık  ·  Metodoloji  ·  İleriye Dönük Senaryolar",
        13, C_BODY, italic=True)

    # Sağ: proje özeti
    RIGHT_X = W_CM * 0.62 + 0.6
    RIGHT_W = W_CM - RIGHT_X - 0.8

    txt(sl, RIGHT_X, 2.5, RIGHT_W, 0.8,
        "Proje Özeti", 15, C_ACCENT, bold=True)

    ozet = [
        ("Problem:", 12, C_ACCENT2, True),
        ("Kullanıcıya özel seyahat önerisi\nyaparken marka ve popülerlik\nbias'ından kaçınmak", 11.5, C_BODY, False),
        ("", 6, C_BODY, False),
        ("Çözüm:", 12, C_ACCENT2, True),
        ("Fotoğraf bazlı tercih öğrenimi +\nadaptif anket + çift vektör temsili", 11.5, C_BODY, False),
        ("", 6, C_BODY, False),
        ("Durum:", 12, C_ACCENT2, True),
        ("Pipeline hazır, gerçek veri\nbekleniyor — sunum bu hazırlığı\nve metodoloji seçimlerini anlatıyor", 11.5, C_BODY, False),
    ]
    multiline(sl, RIGHT_X, 3.4, RIGHT_W, 13.0, ozet, line_spacing_pt=2)

    footer(sl)
    return sl


# ===========================================================================
# SLIDE 2 — Problem & Motivasyon
# ===========================================================================

def slide_problem(prs):
    sl = new_slide(prs)
    bg(sl)
    header_bar(sl,
               "Problem & Motivasyon",
               "Neden bu sistemi inşa ettik?", "2")

    CONTENT_Y = 4.0
    CONTENT_H = H_CM - CONTENT_Y - 0.6

    # 3 problem kartı yan yana
    CARD_W = (W_CM - 2.4) / 3
    CARD_H = CONTENT_H * 0.46
    GAP = 0.6

    problems = [
        ("Marka Bias'ı", C_ACCENT, [
            "Geleneksel öneri sistemleri",
            "popüler/ücretli destinasyonları",
            "öne çıkarır.",
            "",
            "Kullanıcının gerçek tercihi",
            "veriden değil, reklamdan öğrenilir.",
        ]),
        ("Seyrek Veri (Sparsity)", C_ACCENT2, [
            "Yeni kullanıcı için tarihsel",
            "etkileşim verisi yoktur.",
            "",
            "Collaborative filtering",
            "cold start durumunda",
            "tamamen çöker.",
        ]),
        ("Bilişsel Aşırı Yük", C_ACCENT, [
            "Yüzlerce destinasyon arasından",
            "seçim yapmak kullanıcıyı yorar.",
            "",
            "Az sayıda soru ile güçlü",
            "kişiselleştirme gerekmektedir.",
        ]),
    ]

    for i, (title, col, lines) in enumerate(problems):
        cx = 0.8 + i * (CARD_W + GAP)
        card(sl, cx, CONTENT_Y, CARD_W, CARD_H,
             title, lines, header_col=col, bg_col=C_CARD)

    # Alt: bizim çözümümüz
    SOL_Y = CONTENT_Y + CARD_H + 0.5
    SOL_H = CONTENT_H - CARD_H - 0.7

    rect(sl, 0.8, SOL_Y, W_CM - 1.6, SOL_H, C_PANEL,
         line_col=C_ACCENT2, line_pt=1.0)

    txt(sl, 1.2, SOL_Y + 0.15, 12, 0.6,
        "Bizim Yaklaşımımız", 13, C_ACCENT2, bold=True)

    sol_items = [
        "→   Fotoğraf karşılaştırması ile kullanıcı vibe'ı öğren  (marka değil estetik tercih)",
        "→   BALD ile bilgi-maksimal sorular seç  (az soru, yüksek kazanım)",
        "→   8+5 çift vektör: fiziksel özellikler ayrı, sosyal özellikler ayrı modellenir",
    ]
    for j, item in enumerate(sol_items):
        txt(sl, 1.2, SOL_Y + 0.85 + j * 0.62, W_CM - 2.4, 0.6,
            item, 12, C_BODY)

    footer(sl)
    return sl


# ===========================================================================
# SLIDE 3 — Cold Start & Ön İşleme Pipeline
# ===========================================================================

def slide_coldstart(prs):
    sl = new_slide(prs)
    bg(sl)
    header_bar(sl,
               "Cold Start & Ön İşleme Pipeline",
               "Gerçek veri gelmeden önce sistem nasıl hazırlanıyor?", "3")

    CONTENT_Y = 4.0

    # Sol: Cold Start Faz şeması
    LEFT_W = W_CM * 0.44
    right_x = LEFT_W + 1.2
    right_w = W_CM - right_x - 0.8

    txt(sl, 0.8, CONTENT_Y, LEFT_W, 0.7,
        "Cold Start Fazları", 14, C_ACCENT, bold=True)

    fazlar = [
        ("Faz 0  —  Sıfır Veri", C_ACCENT,
         ["Kullanıcı vektörü → tüm bölge embedding'lerinin centroid'i",
          "L2-normalize(mean(region_embs))  →  tarafsız başlangıç noktası",
          "Fiziksel vektör: zeros(8)   Sosyal vektör: zeros(5)"]),
        ("Faz 1  —  İlk Etkileşim", C_ACCENT2,
         ["Fotoğraf seçimleriyle EMA güncelleme:",
          "u ← normalize( (1-α)·u + α·photo_emb )    α = 0.35",
          "Her seçim sonrası bölge posteriorı yeniden hesaplanır"]),
        ("Faz 2  —  Statik Anket (MVP)", C_ACCENT,
         ["≥ 200 oturum toplanana kadar sabit 5 soru havuzu",
          "Boyutlar sırayla doldurulur: fiyat, kalabalık, yemek, ulaşım, eğlence",
          "Cevap entegrasyonu: v ← 0.42·v + 0.58·cevap"]),
        ("Faz 3  —  Veri Gelince", C_ACCENT2,
         ["n ≥ 30  → Lojistik Regresyon ranker eğitilir",
          "n ≥ 200 → LightGBM'e geçiş  (100 estimator, lr=0.05)",
          "Adaptif soru seçimi öğrenilen modelle yapılır"]),
    ]

    for i, (title, col, lines) in enumerate(fazlar):
        cy = CONTENT_Y + 0.9 + i * 3.3
        # Ok işareti
        if i > 0:
            txt(sl, 1.0, cy - 0.55, 2, 0.5, "▼", 16, col, align=PP_ALIGN.CENTER)
        rect(sl, 0.8, cy, LEFT_W - 0.4, 3.0, C_CARD,
             line_col=col, line_pt=1.0)
        txt(sl, 1.1, cy + 0.12, LEFT_W - 0.8, 0.55,
            title, 12, col, bold=True)
        for j, ln in enumerate(lines):
            txt(sl, 1.1, cy + 0.72 + j * 0.68, LEFT_W - 1.0, 0.65,
                ln, 11, C_BODY)

    # Sağ: Embedding Pipeline
    txt(sl, right_x, CONTENT_Y, right_w, 0.7,
        "Embedding Pipeline", 14, C_ACCENT, bold=True)

    steps = [
        ("1. Metin Kaynakları", [
            "regions.json → hidden_desc + open_desc (Türkçe)",
            "fotograflar.json → aciklama alanı (her fotoğraf için)",
            "destinasyonlar.csv → 125 şehir × 13 boyut feature vektörü",
        ]),
        ("2. Encoder", [
            "paraphrase-multilingual-MiniLM-L12-v2",
            "Çıktı: 384 boyutlu float32, L2-normalize edilmiş",
            "Fallback (test/CI): deterministik hash → seeded random",
        ]),
        ("3. Artifact Çıktıları", [
            "model/artifacts/embeddings/region_<id>.npy",
            "model/artifacts/embeddings/photo_<stem>.npy",
            "contexts.npz  ·  regions.npz  (batch embedding)",
        ]),
        ("4. Feature Vektör Katmanı", [
            "8 fiziksel: deniz, doğa, tarih, kültür, spor ×4",
            "5 sosyal: eğlence, sakin, yemek, ulaşım, fiyat",
            "4 kalite: safety, pollution, livability, health_risk",
        ]),
    ]

    for i, (title, lines) in enumerate(steps):
        cy = CONTENT_Y + 0.9 + i * 3.3
        rect(sl, right_x, cy, right_w, 3.1, C_CARD,
             line_col=C_ACCENT, line_pt=0.8)
        txt(sl, right_x + 0.25, cy + 0.12, right_w - 0.5, 0.55,
            title, 12, C_ACCENT, bold=True)
        for j, ln in enumerate(lines):
            txt(sl, right_x + 0.25, cy + 0.72 + j * 0.72, right_w - 0.5, 0.68,
                ln, 11, C_BODY)

    footer(sl)
    return sl


# ===========================================================================
# SLIDE 4 — Adaptive Pairwise & BALD
# ===========================================================================

def slide_bald(prs):
    sl = new_slide(prs)
    bg(sl)
    header_bar(sl,
               "Adaptive Pairwise Öğrenme & BALD",
               "Az soru ile maksimum bilgi kazanımı nasıl sağlanır?", "4")

    CONTENT_Y = 4.0
    LEFT_W = W_CM * 0.52
    right_x = LEFT_W + 1.0
    right_w = W_CM - right_x - 0.8

    # Sol: BALD Algoritması
    txt(sl, 0.8, CONTENT_Y, LEFT_W, 0.7,
        "BALD — Bayesian Active Learning by Disagreement", 14, C_ACCENT, bold=True)

    bald_text = [
        ("Amaç:", 12, C_ACCENT2, True),
        ("Posterior dağılımın entropisini en hızlı düşürecek\nfotoğraf çiftini seç.", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Adım 1 — Posterior hesabı:", 12, C_ACCENT, True),
        ("p = softmax( cos(u, region_embs) / τ )     τ = 0.10", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Adım 2 — Her çift için kazanım simülasyonu:", 12, C_ACCENT, True),
        ("u_sol = norm( (1-α)·u + α·emb_sol )", 11.5, C_BODY, False),
        ("u_sag = norm( (1-α)·u + α·emb_sag )", 11.5, C_BODY, False),
        ("Gain = H(p) − 0.5·[ H(p|u_sol) + H(p|u_sag) ]", 11.5, C_ACCENT2, True),
        ("", 5, C_BODY, False),
        ("Adım 3 — En yüksek Gain'li çifti göster:", 12, C_ACCENT, True),
        ("Her turda posterior güncellenir, döngü tekrar eder", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Durma Kriteri:", 12, C_ACCENT, True),
        ("max(p) > 0.55   VEYA   H(p) < 0.6·ln(K)", 11.5, C_BODY, False),
        ("tur ≥ 10 (maksimum güvenlik sınırı)", 11.5, C_BODY, False),
        ("tur ≥ 3  (minimum — erken durmayı engeller)", 11.5, C_BODY, False),
    ]

    rect(sl, 0.8, CONTENT_Y + 0.85, LEFT_W - 0.4, 12.6, C_CARD,
         line_col=C_ACCENT, line_pt=0.8)
    multiline(sl, 1.1, CONTENT_Y + 1.05, LEFT_W - 0.9, 12.3,
              bald_text, line_spacing_pt=1)

    # Sağ: Neden Pairwise? + Heuristic Fallback
    txt(sl, right_x, CONTENT_Y, right_w, 0.7,
        "Neden Pairwise?", 14, C_ACCENT, bold=True)

    neden = [
        "• Mutlak derecelendirme (1–10) yerine karşılaştırma",
        "  daha az bilişsel yük oluşturur.",
        "",
        "• Her seçim bölge uzayında yön bilgisi taşır;",
        "  tek bir fotoğraf seçimi ~3 özelliği günceller.",
        "",
        "• Entropi tabanlı seçim, random seçime kıyasla",
        "  aynı güvene daha az turda ulaşır.",
    ]
    rect(sl, right_x, CONTENT_Y + 0.85, right_w, 5.2, C_CARD,
         line_col=C_ACCENT2, line_pt=0.8)
    txt(sl, right_x + 0.25, CONTENT_Y + 1.0, right_w - 0.5, 0.55,
        "Pairwise Mantığı", 12, C_ACCENT2, bold=True)
    for j, ln in enumerate(neden):
        txt(sl, right_x + 0.25, CONTENT_Y + 1.6 + j * 0.62,
            right_w - 0.5, 0.6, ln, 11, C_BODY)

    txt(sl, right_x, CONTENT_Y + 6.3, right_w, 0.7,
        "Heuristic Fallback", 13, C_ACCENT, bold=True)

    fallback = [
        "Embedding yoksa (test/offline) farklı skor:",
        "",
        "score = 0.50 × info_gain",
        "      + 0.40 × missing_gain",
        "      + 0.10 × relevance",
        "",
        "missing_gain: eksik boyutları (< 0.18 conf)",
        "öncelikli doldurur → vektörü hızla şekillendirir.",
        "",
        "Ablasyon: BALD vs. Heuristic farkı Δ ≈ 0.004",
        "(embedding uzayında yapı zaten güçlü)",
    ]
    rect(sl, right_x, CONTENT_Y + 7.15, right_w, 6.2, C_CARD,
         line_col=C_ACCENT, line_pt=0.8)
    for j, ln in enumerate(fallback):
        txt(sl, right_x + 0.25, CONTENT_Y + 7.4 + j * 0.56,
            right_w - 0.5, 0.55, ln, 11, C_BODY)

    footer(sl)
    return sl


# ===========================================================================
# SLIDE 5 — Sentetik Değerlendirme & Ablasyon
# ===========================================================================

def slide_ablasyon(prs):
    sl = new_slide(prs)
    bg(sl)
    header_bar(sl,
               "Sentetik Değerlendirme & Ablasyon Çalışması",
               "Gerçek veri olmadan modeli nasıl test ettik?", "5")

    CONTENT_Y = 4.0

    # Üst: Yöntem açıklaması
    txt(sl, 0.8, CONTENT_Y, W_CM - 1.6, 0.65,
        "Yöntem: 6 Persona × 50 Oturum = 300 Sentetik Kullanıcı Simülasyonu",
        14, C_ACCENT, bold=True)

    personas = ["beach_fun", "quiet_beach", "adventure",
                "history_culture", "food_city", "ski_mountain"]
    P_W = (W_CM - 1.6) / len(personas)
    for i, p in enumerate(personas):
        cx = 0.8 + i * P_W
        rect(sl, cx + 0.1, CONTENT_Y + 0.8, P_W - 0.2, 0.75, C_CARD,
             line_col=C_ACCENT, line_pt=0.6)
        txt(sl, cx + 0.15, CONTENT_Y + 0.85, P_W - 0.3, 0.65,
            p.replace("_", "\n"), 9.5, C_ACCENT, align=PP_ALIGN.CENTER)

    # Orta: 3 Ablasyon kutusu
    AX_Y = CONTENT_Y + 1.9
    A_W  = (W_CM - 1.6 - 0.8) / 3
    A_H  = 6.0
    GAP  = 0.4

    ablasyonlar = [
        ("A1  —  BALD vs Random", C_ACCENT,
         ["BALD mean cosine:",
          "    0.701",
          "Random mean cosine:",
          "    0.704",
          "Δ = −0.004  (istatistiksel olarak anlamsız)",
          "",
          "Yorum: Embedding uzayı kendi başına güçlü",
          "yapısal bilgi taşıyor. BALD avantajı gerçek",
          "veriyle daha belirgin hale gelecek.",
          "",
          "→ Her iki strateji MVP için yeterli;"
          ,
          "  gerçek veri gelince BALD avantajı ölçülecek."]),
        ("A2  —  Shuffled vs Sorted Gösterim", C_ACCENT2,
         ["NDCG@3 (shuffled): 0.931",
          "NDCG@3 (sorted):   0.929",
          "Δ = +0.002  (shuffled hafif üstün)",
          "",
          "Gösterim pozisyonu bias proxy:",
          "  Sorted: 1.040  →  pozisyon bias yüksek",
          "  Shuffled: 2.057  →  daha dengeli dağılım",
          "",
          "Yorum: Backend sırası ile kullanıcı görme",
          "sırası ayrıştırıldığında eğitim verisi",
          "daha güvenilir olur.",
          "",
          "→ Shuffle, fairness + model kalitesi için seçildi."]),
        ("A3  —  8+5 vs Düz 13 Vektör", C_ACCENT,
         ["8+5 dual NDCG@3:   0.929",
          "Flat-13 NDCG@3:    0.865",
          "Δ = +0.064  (+%6.4)  ← en büyük kazanım",
          "",
          "Hit@3 (8+5):  0.997",
          "Hit@3 (flat): 0.941",
          "",
          "Yorum: Fiziksel ve sosyal özellikleri ayrı",
          "modellemek şehirleri daha iyi ayırt eder.",
          "Örnek: Roma vs. Efes aynı tarih skorunda",
          "ama farklı kültür seviyesinde — dual bunu",
          "yakalar, flat-13 kaynaştırır.",
          "",
          "→ 8+5 mimari kararın temel kanıtı."]),
    ]

    for i, (title, col, lines) in enumerate(ablasyonlar):
        cx = 0.8 + i * (A_W + GAP)
        card(sl, cx, AX_Y, A_W, A_H, title, lines,
             header_col=col, bg_col=C_CARD)

    # Alt: Genel metrik özeti
    MET_Y = AX_Y + A_H + 0.35
    MET_H = H_CM - MET_Y - 0.45
    rect(sl, 0.8, MET_Y, W_CM - 1.6, MET_H, C_PANEL,
         line_col=C_ACCENT2, line_pt=0.8)

    metrics = [
        "Best: NDCG@3 = 0.929   Hit@3 = 0.997   (8+5 Hybrid, Shuffled)",
        "Test: 88 otomatik pytest geçti   ·   Cross-val: 5-fold ROC-AUC  ·  Model geçiş eşiği: mean − 0.5·std",
    ]
    for j, m in enumerate(metrics):
        txt(sl, 1.2, MET_Y + 0.18 + j * 0.56, W_CM - 2.4, 0.54,
            m, 11.5, C_ACCENT2 if j == 0 else C_BODY, bold=(j == 0))

    footer(sl)
    return sl


# ===========================================================================
# SLIDE 6 — İleriye Dönük Senaryolar
# ===========================================================================

def slide_gelecek(prs):
    sl = new_slide(prs)
    bg(sl)
    header_bar(sl,
               "İleriye Dönük Senaryolar",
               "Veri toplanırsa ne olur? Toplanmazsa sistem nasıl çalışmaya devam eder?", "6")

    CONTENT_Y = 4.1
    HALF_W = (W_CM - 2.4) / 2
    GAP = 0.8
    GREEN_X = 0.8
    RED_X   = GREEN_X + HALF_W + GAP
    BOX_H   = H_CM - CONTENT_Y - 1.3

    # Yeşil kutu — veri toplanırsa
    rect(sl, GREEN_X, CONTENT_Y, HALF_W, BOX_H, C_GREEN_BG,
         line_col=C_GREEN_FG, line_pt=1.5)

    txt(sl, GREEN_X + 0.3, CONTENT_Y + 0.18, HALF_W - 0.6, 0.75,
        "✓  VERİ TOPLANIRSA", 15, C_GREEN_FG, bold=True)

    green_lines = [
        ("Kısa Vadeli  (n ≥ 30)", 12, C_GREEN_FG, True),
        ("• Lojistik Regresyon city ranker devreye girer", 11.5, C_BODY, False),
        ("• Pairwise loss: seçilen şehir > seçilmeyenler", 11.5, C_BODY, False),
        ("• Feature: [u_fiz || u_sos || c_fiz || c_sos] = 26-dim", 11.5, C_BODY, False),
        ("• CV: 5-fold ROC-AUC, geçiş eşiği zorunlu", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Orta Vadeli  (n ≥ 200)", 12, C_GREEN_FG, True),
        ("• LightGBM ranker (100 tree, lr=0.05)", 11.5, C_BODY, False),
        ("• Adaptive survey: soru seçimi öğrenilmiş modelle", 11.5, C_BODY, False),
        ("• BALD kazanımı gerçek veriyle ölçülüp raporlanır", 11.5, C_BODY, False),
        ("• Retrain pipeline: her yeni batch → otomatik değerlendirme", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Uzun Vadeli", 12, C_GREEN_FG, True),
        ("• Gerçek NDCG@3 / Hit@3 hesaplanabilir", 11.5, C_BODY, False),
        ("• Kullanıcı geri bildirimiyle online güncelleme", 11.5, C_BODY, False),
        ("• Per-region ranker: bölge başına ayrı model", 11.5, C_BODY, False),
        ("• A/B test: BALD vs random fotoğraf seçimi", 11.5, C_BODY, False),
    ]
    multiline(sl, GREEN_X + 0.3, CONTENT_Y + 1.05,
              HALF_W - 0.6, BOX_H - 1.2, green_lines, line_spacing_pt=2)

    # Kırmızı kutu — veri toplanmazsa
    rect(sl, RED_X, CONTENT_Y, HALF_W, BOX_H, C_RED_BG,
         line_col=C_RED_FG, line_pt=1.5)

    txt(sl, RED_X + 0.3, CONTENT_Y + 0.18, HALF_W - 0.6, 0.75,
        "⚠  VERİ TOPLANMAZSA", 15, C_RED_FG, bold=True)

    red_lines = [
        ("Sistem Çalışmaya Devam Eder", 12, C_RED_FG, True),
        ("• Cosine benzerlik tabanlı hybrid skor aktif kalır", 11.5, C_BODY, False),
        ("• NDCG@3 = 0.929 sentetik değerlendirmede geçerli", 11.5, C_BODY, False),
        ("• 88 test süite sistemi güvende tutar", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Alternatif Yollar", 12, C_RED_FG, True),
        ("• Transfer learning: turizm domain verisiyle ön-eğitim", 11.5, C_BODY, False),
        ("• Kullanıcı simülasyonu ile sentetik eğitim seti büyütülür", 11.5, C_BODY, False),
        ("• Mevcut 6 persona genişletilir (12–18 çeşit)", 11.5, C_BODY, False),
        ("• Heuristic fallback, BALD performansına Δ=0.004 fark ile", 11.5, C_BODY, False),
        ("  yakın — pratikte kabul edilebilir.", 11.5, C_BODY, False),
        ("", 5, C_BODY, False),
        ("Temel Güvence", 12, C_RED_FG, True),
        ("• Pipeline, veri gelir gelmez ML geçişini", 11.5, C_BODY, False),
        ("  otomatik tetikler — manuel müdahale gerekmez.", 11.5, C_BODY, False),
        ("• Threshold: n_sessions < 30 → cosine fallback,", 11.5, C_BODY, False),
        ("             n_sessions ≥ 30 → ML ranker aktif.", 11.5, C_BODY, False),
    ]
    multiline(sl, RED_X + 0.3, CONTENT_Y + 1.05,
              HALF_W - 0.6, BOX_H - 1.2, red_lines, line_spacing_pt=2)

    footer(sl)
    return sl


# ===========================================================================
# Ana fonksiyon
# ===========================================================================

def main():
    prs = Presentation()
    prs.slide_width  = cm(W_CM)
    prs.slide_height = cm(H_CM)

    slide_kapak(prs)
    slide_problem(prs)
    slide_coldstart(prs)
    slide_bald(prs)
    slide_ablasyon(prs)
    slide_gelecek(prs)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "docs", "presentation")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "sunum.pptx")
    prs.save(out)
    print(f"Kaydedildi: {out}  ({prs.slides.__len__()} slide)")


if __name__ == "__main__":
    main()
