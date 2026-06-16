"""Bilingual strings — TR / EN"""

STRINGS = {
    "TR": {
        # Genel
        "app_title":        "Gezi Rehberi",
        "app_subtitle":     "Adaptif Öneri Sistemi",
        "lang_toggle":      "English",

        # Giriş
        "hero_title":       "Seyahat DNA'nı Keşfet",
        "hero_sub":         "Birkaç seçimle sana en uygun Türkiye destinasyonunu buluyoruz.",
        "how_works":        "Nasıl Çalışır?",
        "step1_title":      "Fotoğraf Seç",
        "step1_desc":       "İki görsel arasında sezgisel seçimler yap.",
        "step2_title":      "Profil Oluşur",
        "step2_desc":       "Her seçim tercih vektörünü şekillendirir.",
        "step3_title":      "Öneri Al",
        "step3_desc":       "Şehirler anonim açıklanır, ardından isimler açılır.",
        "visited_label":    "Daha önce gittiğin şehirleri seç (öneri listesinden çıkarılır):",
        "start_btn":        "Başla →",

        # Fotoğraf
        "which_draws":      "Hangisi seni daha çok çekiyor?",
        "instinct_note":    "İçgüdülerine güven — ilk hissin en doğru cevap",
        "this_is_me":       "Bu beni yansıtıyor",
        "confidence_label": "Model güveni",
        "question_label":   "Soru",
        "max_label":        "maks",
        "show_vector":      "Tercih vektörünü göster",

        # Öneri — anonim
        "anon_title":       "Sana Özel 3 Yer Bulundu",
        "anon_sub":         "Şehir isimleri gizli — sadece sana uygunluğuna bak",
        "destination":      "Destinasyon",
        "category_label":   "Kategori",
        "match_label":      "uyum",
        "reveal_btn":       "🔓 Şehirleri Göster",

        # Öneri — açık
        "reveal_title":     "İşte Senin Şehirlerin!",
        "why_title":        "Neden {sehir}? (Kara Kutu)",
        "model_graph":      "Model Analizi Grafiği",
        "feedback_btn":     "Geri Bildirim Ver →",

        # Geri bildirim
        "fb_title":         "Geri Bildirim",
        "fb_sub":           "Her geri bildirim sistemi daha akıllı yapar.",
        "main_suggestion":  "Ana öneri",
        "fb_question":      "Bu öneri seni yansıtıyor mu?",
        "fb_yes":           "Evet, tam istediğim",
        "fb_partial":       "Kısmen",
        "fb_no":            "Hayır, bu değil",
        "fb_closer":        "Hangisi daha yakındı?",
        "fb_correct":       "Doğru şehir:",
        "fb_save":          "Kaydet ve öğren",
        "fb_saved":         "Öğrenildi! Bir sonraki tahmin daha doğru olacak.",
        "fb_thanks":        "Teşekkürler! Geri bildirim kaydedildi.",
        "restart_btn":      "Yeniden başla",
        "choose":           "— Seçin —",

        # Sidebar
        "admin_title":      "Admin",
        "total_records":    "Toplam Kayıt",
        "records_needed":   "Eğitim İçin Gereken",
        "retrain_btn":      "Modeli Yeniden Eğit",
        "retrain_done":     "Model güncellendi!",
        "need_more":        "Eğitim için {n} kayıt daha gerekli.",
        "model_active":     "Model aktif",
        "model_inactive":   "Henüz eğitilmedi",

        # Feature isimleri
        "features": {
            "deniz":     "Deniz",
            "doga":      "Doğa",
            "tarih":     "Tarih",
            "kultur":    "Kültür",
            "eglence":   "Eğlence",
            "sakin":     "Sakin",
            "doga_spor": "Doğa Sporu",
            "su_spor":   "Su Sporu",
            "hava_spor": "Hava Sporu",
            "kis_spor":  "Kış Sporu",
            "yemek":     "Yemek",
            "ulasim_kolayligi": "Ulaşım Kolaylığı",
            "fiyat":     "Bütçe",
        },
    },

    "EN": {
        # General
        "app_title":        "Travel Guide",
        "app_subtitle":     "Adaptive Recommendation System",
        "lang_toggle":      "Türkçe",

        # Intro
        "hero_title":       "Discover Your Travel DNA",
        "hero_sub":         "A few choices are all it takes to find your perfect Turkish destination.",
        "how_works":        "How It Works",
        "step1_title":      "Choose Photos",
        "step1_desc":       "Make intuitive picks between two images.",
        "step2_title":      "Profile Builds",
        "step2_desc":       "Each choice shapes your preference vector.",
        "step3_title":      "Get Recommendations",
        "step3_desc":       "Cities revealed anonymously, then names are shown.",
        "visited_label":    "Select cities you've already visited (excluded from results):",
        "start_btn":        "Start →",

        # Photo
        "which_draws":      "Which one draws you more?",
        "instinct_note":    "Trust your gut — first instinct is the best answer",
        "this_is_me":       "This is me",
        "confidence_label": "Model confidence",
        "question_label":   "Question",
        "max_label":        "max",
        "show_vector":      "Show preference vector",

        # Recommendation — anonymous
        "anon_title":       "3 Places Found for You",
        "anon_sub":         "City names hidden — judge by fit score only",
        "destination":      "Destination",
        "category_label":   "Category",
        "match_label":      "match",
        "reveal_btn":       "🔓 Reveal Cities",

        # Recommendation — revealed
        "reveal_title":     "Your Cities!",
        "why_title":        "Why {sehir}? (Explainability)",
        "model_graph":      "Model Analysis Graph",
        "feedback_btn":     "Give Feedback →",

        # Feedback
        "fb_title":         "Feedback",
        "fb_sub":           "Every feedback makes the system smarter.",
        "main_suggestion":  "Top recommendation",
        "fb_question":      "Does this recommendation reflect you?",
        "fb_yes":           "Yes, exactly what I want",
        "fb_partial":       "Somewhat",
        "fb_no":            "No, not me",
        "fb_closer":        "Which was closer?",
        "fb_correct":       "Correct city:",
        "fb_save":          "Save & learn",
        "fb_saved":         "Learned! Next prediction will be more accurate.",
        "fb_thanks":        "Thank you! Feedback saved.",
        "restart_btn":      "Start over",
        "choose":           "— Select —",

        # Sidebar
        "admin_title":      "Admin",
        "total_records":    "Total Records",
        "records_needed":   "Needed for Training",
        "retrain_btn":      "Retrain Model",
        "retrain_done":     "Model updated!",
        "need_more":        "{n} more records needed for training.",
        "model_active":     "Model active",
        "model_inactive":   "Not trained yet",

        # Feature names
        "features": {
            "deniz":     "Sea",
            "doga":      "Nature",
            "tarih":     "History",
            "kultur":    "Culture",
            "eglence":   "Entertainment",
            "sakin":     "Peaceful",
            "doga_spor": "Outdoor Sports",
            "su_spor":   "Water Sports",
            "hava_spor": "Air Sports",
            "kis_spor":  "Winter Sports",
            "yemek":     "Food",
            "ulasim_kolayligi": "Easy Transport",
            "fiyat":     "Budget",
        },
    },
}


def t(key: str, lang: str = "TR", **kwargs) -> str:
    """Translate a key. kwargs for string formatting."""
    val = STRINGS.get(lang, STRINGS["TR"]).get(key, key)
    if kwargs:
        val = val.format(**kwargs)
    return val


def feat(feature: str, lang: str = "TR") -> str:
    """Translate a feature name."""
    return STRINGS.get(lang, STRINGS["TR"])["features"].get(feature, feature)
