# Methodology Notes

Bu proje, fotoğraf tercihleri ve kısa bağlam cevaplarından 8 fiziksel + 5 sosyolojik boyutlu kullanıcı vektörü çıkaran bir Streamlit MVP'sidir. Final şehir listesi `model/recommend.py` facade'i üzerinden aktif aday havuzuna hybrid ranker uygulanarak üretilir.

## Skorların Yorumu

Ekranda ve raporda kullanılan skorlar gerçek olasılık değildir. Bunlar cosine/hybrid yakınlık, sparse overlap, kalite penalty ve güvenlik tercihi gibi sinyallerin birleşiminden oluşan göreli affinity skorlarıdır. Bu yüzden UI'da yüzde hassasiyeti yerine dot rating ve açıklayıcı metin tercih edilir.

## BALD / Active Learning

Stage 1 fotoğraf seçimi için embedding artifact'leri varsa BALD-style seçim yolu çalışır; artifact yoksa feature-space heuristic fallback kullanılır. Mevcut sentetik ablation'da BALD random baseline'a belirgin üstünlük göstermediği için iddia "kanıtlanmış performans artışı" değil, "aktif öğrenme altyapısı ve fallback zinciri" olarak sunulmalıdır.

## Offline Evaluation

`notebooks/01_synthetic_eval.py` ve `notebooks/ablation_sonuc.md` model içi proxy validation sağlar. Sentetik persona ground truth'u aynı özellik uzayından türediği için bu sonuçlar dış geçerlilik iddiası taşımaz; amaç pipeline regressions ve varyant karşılaştırması yakalamaktır.

## Baseline İhtiyacı

Sunumda NDCG@3 tek başına verilmemelidir. Random, static/popularity, vector-only ve context/text varyantları aynı tabloda gösterilerek "0.9 civarı skor neye göre iyi?" sorusu cevaplanmalıdır.
