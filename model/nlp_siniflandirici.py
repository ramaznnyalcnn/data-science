"""
Şehir yorumlarından otomatik feature skoru çıkarır.
BERT (bert-base-turkish-cased) ile zero-shot sınıflandırma.
RTX 3050 Ti 4GB VRAM'e uygun: sadece inference, batch_size=1.
"""

import torch
import numpy as np
import pandas as pd
import json
import os
from transformers import AutoTokenizer, AutoModel

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "dbmdz/bert-base-turkish-cased"

# Her feature için Türkçe anahtar kelime grubu
FEATURE_TANIMLARI = {
    "deniz":     "deniz plaj koy kumsal yüzme sahil dalga sörf",
    "doga":      "dağ orman yayla göl şelale doğa vadi kanyon çayır",
    "tarih":     "tarihi müze antik kale harabe arkeoloji osmanlı bizans",
    "kultur":    "kültür festival gelenek sanat çarşı pazar yerel halk",
    "eglence":   "eğlence bar kulüp konser aquapark lunapark alışveriş gece",
    "sakin":     "sakin huzurlu sessiz tenha dinlendirici ıssız doğal",
    "doga_spor": "atv kamp trekking yürüyüş dağcılık at binme macera",
    "su_spor":   "rafting sörf dalış tekne kano su kayağı",
    "hava_spor": "balon paraşüt yamaç uçuş hava",
    "kis_spor":  "kayak snowboard kış kar pistler",
    "yemek":     "yemek mutfak lezzet kebap restoran kahvaltı tatlı",
    "ulasim_kolayligi": "toplu taşıma tramvay metro otobüs yürünebilir merkezi araçsız kolay ulaşım",
}

# Fiyat ve mevsim manuel kalır (NLP ile çıkarmak anlamsız)


class BertSiniflandirici:
    def __init__(self):
        print(f"[NLP] Model yükleniyor: {MODEL_NAME} ({DEVICE})")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
        self.model.eval()

        # Feature tanımlarını önceden encode et
        self.feature_embeddings = {}
        for feature, tanim in FEATURE_TANIMLARI.items():
            self.feature_embeddings[feature] = self._encode(tanim)
        print("[NLP] Hazır.")

    def _encode(self, metin: str) -> np.ndarray:
        inputs = self.tokenizer(
            metin,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding=True
        ).to(DEVICE)

        with torch.no_grad():
            cikti = self.model(**inputs)

        # CLS token embedding → şehri/feature'ı temsil eder
        embedding = cikti.last_hidden_state[:, 0, :].squeeze()
        return embedding.cpu().numpy()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def yorumdan_skor_cikar(self, yorumlar: list[str]) -> dict:
        """
        Şehrin yorumları → her feature için 0.0-1.0 skor.
        yorumlar: ['Bodrum çok güzeldi, deniz harikaydı...', ...]
        """
        # Tüm yorumları birleştir ve encode et
        birlesik_metin = " ".join(yorumlar[:20])  # ilk 20 yorum yeter
        sehir_embedding = self._encode(birlesik_metin)

        skorlar = {}
        for feature, feat_embedding in self.feature_embeddings.items():
            cos_sim = self._cosine_similarity(sehir_embedding, feat_embedding)
            # Cosine similarity -1 ile 1 arasında → 0-1'e normalize et
            skor = (cos_sim + 1) / 2
            skorlar[feature] = round(skor, 3)

        return skorlar

    def sehirleri_siniflandir(self, sehir_yorumlari: dict) -> pd.DataFrame:
        """
        Tüm şehirleri sınıflandır ve CSV'ye kaydet.
        sehir_yorumlari: {'Bodrum': ['yorum1', 'yorum2', ...], ...}
        """
        sonuclar = []
        for sehir, yorumlar in sehir_yorumlari.items():
            print(f"  → {sehir} işleniyor...")
            skorlar = self.yorumdan_skor_cikar(yorumlar)
            skorlar["sehir"] = sehir
            sonuclar.append(skorlar)

        df = pd.DataFrame(sonuclar)
        # Sütun sırası
        sutunlar = ["sehir"] + list(FEATURE_TANIMLARI.keys())
        df = df[sutunlar]
        return df


def main():
    # Örnek yorumlar (gerçek Google Maps verisi buraya gelecek)
    ornek_yorumlar = {
        "Bodrum": [
            "Bodrum gece hayatı muhteşem, barlar ve kulüpler çok aktif.",
            "Deniz tertemiz, plajlar bakımlı ama çok kalabalık.",
            "Yat limanı manzarası harika, lüks restoranlar mevcut.",
            "Tarihi kale mutlaka görülmeli.",
        ],
        "Kapadokya": [
            "Balon turu hayatımın en güzel deneyimiydi.",
            "Peri bacaları arasında yürüyüş unutulmaz.",
            "Tarihi yeraltı şehirleri etkileyici.",
            "ATV turu çok eğlenceliydi, doğa muhteşem.",
            "Sakin ve huzurlu bir atmosfer var.",
        ],
        "Gaziantep": [
            "Türkiye'nin en iyi mutfağı burada.",
            "Baklavanın ve kebabın gerçek tadı Gaziantep'te.",
            "Tarihi çarşı ve bakır işleri ilginç.",
            "Zeugma mozaik müzesi kesinlikle görülmeli.",
        ],
    }

    siniflandirici = BertSiniflandirici()
    df = siniflandirici.sehirleri_siniflandir(ornek_yorumlar)

    print("\n=== NLP Sınıflandırma Sonuçları ===")
    print(df.to_string(index=False))

    # Kaydet
    cikti_yolu = os.path.join(
        os.path.dirname(__file__), "..", "data", "nlp_sehir_skorlari.csv"
    )
    df.to_csv(cikti_yolu, index=False)
    print(f"\n[NLP] Kaydedildi: {cikti_yolu}")


if __name__ == "__main__":
    main()
