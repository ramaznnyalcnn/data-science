# Sentetik Ablation Sonuclari

- 125 destinasyon, 6 persona, 50 oturum/persona
- Ground truth proxy: her persona icin hybrid skora gore en yakin 8 destinasyon
- Seed: 42

## Skor Varyantlari

| Senaryo | NDCG@3 | Hit@3 |
|---|---:|---:|
| Random ranking | 0.048 | 0.147 |
| Static data order | 0.128 | 0.167 |
| Baseline flat cosine | 0.864 | 0.977 |
| Weighted flat cosine | 0.865 | 0.977 |
| Dual weighted cosine | 0.929 | 0.997 |
| Hybrid score | 0.929 | 0.997 |
| Full oneri_yap pipeline | 0.918 | 0.990 |

## A1 - BALD vs Random Pair

| Metric | Value |
|---|---:|
| BALD mean persona cosine | 0.807 |
| Random mean persona cosine | 0.704 |
| Delta | 0.103 |

## A2 - Sorted vs Shuffled Display

| Metric | Value |
|---|---:|
| Sorted NDCG@3 | 0.927 |
| Shuffled display NDCG@3 | 0.931 |
| Sorted shown-position proxy | 1.040 |
| Shuffled shown-position proxy | 2.057 |

## A3 - Dual 8+5 vs Flat 13

| Metric | Value |
|---|---:|
| Flat 13 NDCG@3 | 0.865 |
| Flat 13 Hit@3 | 0.977 |
| Dual 8+5 NDCG@3 | 0.929 |
| Dual 8+5 Hit@3 | 0.997 |
| NDCG Delta | 0.064 |

## Full Pipeline Persona Kirilimi

| Persona | NDCG@3 | Hit@3 |
|---|---:|---:|
| Deniz ve eglence | 1.000 | 1.000 |
| Sakin sahil | 0.980 | 1.000 |
| Doga ve macera | 0.986 | 1.000 |
| Tarih ve kultur | 0.643 | 0.940 |
| Yemek ve sehir | 0.953 | 1.000 |
| Kis ve dag | 0.944 | 1.000 |
