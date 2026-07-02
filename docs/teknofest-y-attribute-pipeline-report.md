# Y Attribute Pipeline Raporu

Tarih: 2026-07-02
Proje: `e-ticaret_teknofest`

## Kisa Ozet

Bu calismada mevcut guvenli anchor submission korunarak, sadece cok guvenli oldugu dusunulen yeni pozitifleri ekleyecek ikinci bir Y attribute-compatibility sistemi kuruldu.

Ana hedef: anchor'in kacirdigi pozitifleri yakalamak, fakat anchor'daki mevcut pozitifleri asla kapatmamak.

Temel prensip:

- X / anchor mevcut guvenli submission'dir.
- Y modeli query ile item attribute'lari gercekten uyumlu mu ogrenmeye calisir.
- Add-only gate sadece `anchor=0` satirlara ekleme yapabilir.
- `anchor=1` hicbir satir `0` yapilmaz.
- `hard_conflict` varsa Y skoru yuksek olsa bile ekleme engellenir.

## Ana Strateji

| Parca | Mantik |
|---|---|
| X / anchor | Mevcut guvenli submission. Korunur. |
| Y model | Query-item attribute uyumlulugunu ogrenir. |
| Add-only gate | Sadece anchor negatiflerine pozitif ekler. |
| hard_conflict | Kesin celiskili adaylari bloke eder. |
| Audit | Add-only, pozitif oran ve kategori kaymasini kontrol eder. |

## Su Ana Kadar Tamamlananlar

| Is | Durum | Aciklama / Cikti |
|---|---:|---|
| Y embedding cache | Tamamlandi | `experiments/_cache/y_attribute/trnorm_v2_yattr_v1` |
| Cache dogrulama | Tamamlandi | `50,153` term, `962,873` item, `1024` dim, `float16` |
| OOM problemi analizi | Tamamlandi | Ilk training cluster fazinda exit `137` ile memory kill olmustu |
| Cluster OOM fix | Tamamlandi | `scripts/y_attribute_clusters.py` batch cluster yapacak sekilde patchlendi |
| Focused tests | Tamamlandi | `pytest scripts/test_y_attribute_compat.py` gecti |
| Cluster smoke test | Tamamlandi | Kucuk in-memory cluster testi gecti |
| Y cluster store | Tamamlandi | `models/y_attribute_clusters.joblib` yazildi |
| Query/product clustering | Tamamlandi | Query cluster + product cluster uretildi |
| Top/gender/age/material subclusters | Tamamlandi | top `15`, gender `4`, age `6`, attr `105` grup |
| Family-disjoint split | Tamamlandi | train `199,292`, valid `50,708` |
| Same-category/top negatives | Tamamlandi | train `397,505`, valid `101,177` negatif |
| Finish pipeline script | Tamamlandi | `scripts/run_y_attribute_finish_pipeline.sh` |
| Finish pipeline baslatma | Tamamlandi | Tmux'ta Y artifact bekliyor |

## Su An Devam Eden Asama

Egitim su anda `Generating explicit contradiction negatives` fazinda calisiyor.

Bu faz log olarak sessiz, fakat CPU kullaniyor. Bu nedenle surec uyumus/stuck gibi gorunse de CPU time artisi ilerledigini gosteriyor.

Calisan surecler:

| Surec | Tmux | PID | Durum |
|---|---|---:|---|
| Y training | `yattr_compat_20260702b` | `686411` | Calisiyor |
| Finish pipeline | `yattr_finish_pipeline_20260702` | `691837` | Y artifact bekliyor |

Log dosyalari:

- Training log: `logs/y_attr_compat_20260702_0918.log`
- Pipeline log: `logs/y_attr_finish_pipeline_20260702_0941.log`

## Bekleyen Isler

| Asama | Durum | Ne olacak |
|---|---:|---|
| Explicit contradiction negatives | Devam ediyor | Hard/adversarial negatifler uretilecek |
| Y feature build | Bekliyor | Train/valid Y feature frame kurulacak |
| Y0-Y4 CatBoost training | Bekliyor | 5 varyant egitilecek |
| Y model artifacts | Bekliyor | `.cbm`, bundle, manifest, metrics yazilacak |
| Full Y add-only scoring | Bekliyor | Submission pairs uzerinde Y score hesaplanacak |
| Audit | Bekliyor | `candidate_audit.csv`, `category_shift.csv`, `run_summary.json` |
| G gate | Sartli | Y audit gecer ve OOF hazirsa calisacak |
| Final submission | Bekliyor | `to_upload/y_attribute_pipeline/final_submission.csv` |

## Explicit Contradiction Negative Mantigi

Bu faz Y modelinin kesin celiskileri ogrenmesi icin guclu negatif ornekler uretir.

| Negatif tipi | Mantik |
|---|---|
| brand violation | Query belirli marka istiyor, item baska marka |
| gender violation | Query erkek/kadin diyor, item ters cinsiyet |
| model violation | Query iPhone 14 gibi model istiyor, item iPhone 11 gibi baska model |
| unit/pack violation | 50 ml vs 100 ml, 2'li vs 1'li gibi farklar |
| accessory negative | Ana urun yerine kilif/kordon/aksesuar |
| near category distractor | Ayni ust kategori ama yanlis leaf/product type |
| crossterm | Baska query'nin pozitifini bu query icin zor negatif yapmak |

## Y Feature Mantigi

Y modeli sadece cluster'a bakmaz. Uc ana sinyal grubu vardir.

| Feature grubu | Ne yapar |
|---|---|
| Embedding proof | Query-item global semantic benzerligi ve field bazli benzerlik |
| Field proof | `color`, `size`, `model`, `quantity`, `unit`, `pack_count` uyumu |
| Explicit conflict | Kesin celiskiler: model, olcu, pack, gender, age, accessory |

Onemli kesin celiskiler sistemde vardir:

| Celiski | Durum | Feature |
|---|---:|---|
| model conflict | Var | `proof_model_conflict`, `ent_model_conflict` |
| size conflict | Var | `proof_size_conflict` |
| unit/measure conflict | Var | `proof_measure_conflict`, `ent_measure_conflict` |
| pack-count conflict | Var | `ent_pack_conflict` |
| final hard block | Var | `hard_conflict` |

Not: Pack-count icin kolon adi `proof_pack_conflict` degil, `ent_pack_conflict`. Ancak `hard_conflict` icine dahil edildigi icin add-only gate tarafinda guvenlik etkisi vardir.

## Y Varyant Mantigi

| Varyant | Icerik | Amac |
|---|---|---|
| Y0 | Sadece embedding/field similarity | Temel semantic proof |
| Y1 | Y0 + product cluster | Urun cluster etkisi |
| Y2 | Y1 + query-product cluster iliskisi | Cift cluster katkisi |
| Y3 | Y2 + explicit proof/conflict features | Kesin attribute proof katkisi |
| Y4 | Tum feature'lar | En guclu/tam model |

Y3 ve Y4 explicit `proof_` / `ent_` feature'lari icerir. Final add-only scoring'de ayrica `hard_conflict` gate uygulanir.

## Finish Pipeline Mantigi

Pipeline script'i: `scripts/run_y_attribute_finish_pipeline.sh`

Calisma sirasinda sunlari yapar:

1. Y training artifact'larini bekler.
2. `y_attribute_compat_bundle.joblib` ve manifest hazir olunca full submission scoring'e gecer.
3. Y add-only submission yazar.
4. Audit dosyalarini uretir.
5. Y audit gecer ve OOF dosyasi varsa G gate egitir/skorlar.
6. Secilen final adayi `to_upload/y_attribute_pipeline/final_submission.csv` olarak kopyalar.

Beklenen Y scoring ciktilari:

- `to_upload/y_attribute_gate/y_scores.csv`
- `to_upload/y_attribute_gate/submission_y_add_only.csv`
- `to_upload/y_attribute_gate/candidate_audit.csv`
- `to_upload/y_attribute_gate/category_shift.csv`
- `to_upload/y_attribute_gate/run_summary.json`

Beklenen final cikti:

- `to_upload/y_attribute_pipeline/final_submission.csv`
- `to_upload/y_attribute_pipeline/pipeline_summary.json`

## Submission Gunu Sirasi

Gunde 5 hak varsa planlanan sira:

| Sira | Aday | Sart / Amac |
|---:|---|---|
| 1 | Y4 add-only | En guvenli aday, `hard_conflict` gate acik |
| 2 | Y4 raw | Y'nin filtresiz gercek gucunu olcmek |
| 3 | Y2 add-only | Embedding + cift cluster katkisini olcmek |
| 4 | 0.80 X + 0.20 Y4 blend | Sabit agirlikli benchmark |
| 5 | G gate | Yalniz OOF düzgün egitilmis ve audit gecmisse; degilse Y3 add-only |

## Hazir Olan Submission Adaylari

Su an yeni Y/G adaylarindan hazir olan yok.

Hazir olan mevcut dosya:

- `to_upload/v12_anchor/submission_rate242.csv`

Bu mevcut anchor'dir, yeni Y pipeline ciktisi degildir.

Yeni adaylarin durumu:

| Aday | Hazir mi? | Sebep |
|---|---:|---|
| Y4 add-only | Hayir | Y model egitimi bitmedi |
| Y4 raw | Hayir | Y4 model artifact yok |
| Y2 add-only | Hayir | Y2 model artifact yok |
| 0.80 X + 0.20 Y4 blend | Hayir | Y4 score yok |
| G gate | Hayir | Y OOF + audit sonrasi mumkun |

## Risk ve Karar Notlari

- Ilk cluster denemesi memory nedeniyle oldu; bu problem batch cluster patch'i ile asildi.
- Su anki uzun kisim adversarial negative uretimi.
- Surec CPU kullandigi icin tamamen takildi demek dogru degil.
- Eger bu faz makul olmayan sekilde uzarsa hizli fallback secenegi: daha dusuk `--adv-pool-cap` veya `--skip-adversarial` ile yeniden egitim.
- Fallback daha hizli sonuc verir ama adversarial guvenlik sinyalinden bir miktar feragat eder.

## Son Durum

Su ana kadar altyapi, cache, cluster, OOM fix, testler ve pipeline hazirlandi. Egitim aktif olarak adversarial negative fazinda calisiyor. Y modeli tamamlandiginda pipeline otomatik olarak scoring, audit ve final aday uretimine gececek.
