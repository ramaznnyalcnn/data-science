# Limitations

## Validation

Gerçek kullanıcı pilotu henüz sınırlıdır; `data/sessions.jsonl` pilot toplama kanalıdır ve `.gitignore` altındadır. Mevcut otomatik değerlendirme sentetik persona tabanlıdır, dış geçerlilik için 10-15 kişilik mini pilot gerekir.

## Embeddings

Plan dokümanlarında CLIP/SigLIP yönü tartışılsa da MVP canlı yolunda fotoğraf ve bölge embedding'leri text-proxy açıklamalardan üretilir. Bu, demo ve ablation için yeterli bir proxy'dir; gerçek görsel embedding entegrasyonu future work olarak kalır.

## Calibration

Affinity skorları kalibre edilmemiştir. Brier score veya ECE ölçülmeden skorlar "olasılık" veya "% uyum" olarak sunulmamalıdır.

## Known Weak Spots

Tarih+kültür personası diğer sentetik personalara göre daha zayıf ayrışır. Bunun muhtemel nedeni tarih, kültür, yemek ve şehir temposu sinyallerinin veri setinde yüksek korelasyonlu olmasıdır. Persona-spesifik anchor tuning future work olarak ele alınmalıdır.

## Explainability

Mevcut açıklamalar en güçlü pozitif katkıları gösterir. "Neden bu şehir değil?" türü kontra-açıklamalar henüz yoktur; karşılaştırmalı açıklama katmanı ayrı bir geliştirme olarak planlanmalıdır.
