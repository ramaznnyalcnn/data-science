"""
Model eğitimi: LogisticRegression vs RandomForest karşılaştırması.
- n<MIN_TRAIN_N (varsayılan 30) iken eğitim yapılmaz.
- 5-fold cross-validation ile F1 mean ± std raporlanır (tek-shot accuracy değil).
- İki model denenir, daha yüksek cv_mean olan kazanır ve kaydedilir.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import (
    accuracy_score, classification_report, f1_score,
    confusion_matrix, ConfusionMatrixDisplay,
)

sys.path.append(os.path.dirname(__file__))
from config import FEATURES, MIN_TRAIN_N, CV_FOLDS, QUALITY_FEATURES

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "city_ranker.joblib")
SONUC_PATH = os.path.join(os.path.dirname(__file__), "egitim_sonuclari.json")
MODEL_DATA_PATH = os.path.join(DATA_DIR, "model_destinasyonlar.csv")
SAFETY_DATA_PATH = os.path.join(DATA_DIR, "city_safety.json")


def _merge_quality_layer(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for feature in QUALITY_FEATURES:
        if feature not in out.columns:
            out[feature] = 0.70
    if not os.path.exists(SAFETY_DATA_PATH):
        return out
    with open(SAFETY_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = {city: vals for city, vals in data.items() if city != "_meta"}
    for idx, row in out.iterrows():
        values = rows.get(row["sehir"], {})
        for feature in QUALITY_FEATURES:
            if feature in values:
                out.at[idx, feature] = float(values[feature])
    return out


def _ensure_user_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for feature in FEATURES:
        if feature not in out.columns:
            out[feature] = 0.50 if feature in QUALITY_FEATURES else 0.0
    return out


def veri_yukle():
    df_k = _ensure_user_feature_columns(pd.read_csv(os.path.join(DATA_DIR, "kullanici_veri.csv")))
    sehir_path = MODEL_DATA_PATH if os.path.exists(MODEL_DATA_PATH) else os.path.join(DATA_DIR, "destinasyonlar.csv")
    df_s = _merge_quality_layer(pd.read_csv(sehir_path)).set_index("sehir")

    X, y = [], []
    for _, satir in df_k.iterrows():
        sehir = satir["oneri_sehir"]
        if sehir not in df_s.index:
            continue
        kullanici_v = satir[FEATURES].values.astype(float)
        sehir_v     = df_s.loc[sehir, FEATURES].values.astype(float)
        X.append(np.concatenate([kullanici_v, sehir_v]))
        y.append(int(satir["begendi"]))

    return np.array(X), np.array(y)


def _cv_skor(model, X, y, k):
    """Stratified k-fold CV → (mean, std). Sınıf başına yetersiz örnek varsa düşürür."""
    sinif_min = min(np.bincount(y)) if len(set(y)) > 1 else len(y)
    k_kullanim = max(2, min(k, sinif_min))
    skf = StratifiedKFold(n_splits=k_kullanim, shuffle=True, random_state=42)
    skorlar = cross_val_score(model, X, y, cv=skf, scoring="f1")
    return float(skorlar.mean()), float(skorlar.std()), k_kullanim


def model_egit(X, y, onceki_accuracy=None):
    n = len(X)
    if n < MIN_TRAIN_N:
        print(f"[Eğitim] Yetersiz veri: {n} kayıt (min {MIN_TRAIN_N}). "
              f"Cosine similarity ile devam edilmeli.")
        return None, None

    if len(set(y)) < 2:
        print("[Eğitim] Tek sınıflı veri — eğitim yapılamaz.")
        return None, None

    adaylar = {
        "LogisticRegression": LogisticRegression(
            max_iter=500, C=0.5, class_weight="balanced", random_state=42
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=8, class_weight="balanced",
            random_state=42, n_jobs=-1,
        ),
    }

    print(f"\n[Eğitim] {n} kayıt — {CV_FOLDS}-fold CV ile model karşılaştırması:")
    cv_sonuc = {}
    for ad, m in adaylar.items():
        mean, std, k = _cv_skor(m, X, y, CV_FOLDS)
        cv_sonuc[ad] = {"mean": mean, "std": std, "k": k}
        print(f"  {ad:20s} cv_f1 = {mean:.3f} ± {std:.3f}  (k={k})")

    # Kazananı seç
    kazanan_ad = max(cv_sonuc, key=lambda a: cv_sonuc[a]["mean"])
    kazanan = adaylar[kazanan_ad]
    kazanan_cv = cv_sonuc[kazanan_ad]
    print(f"\n  → Kazanan: {kazanan_ad}")

    # Tüm veriyle final fit + holdout rapor
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    kazanan.fit(X_train, y_train)
    y_pred = kazanan.predict(X_test)
    holdout_acc = accuracy_score(y_test, y_pred)
    holdout_f1 = f1_score(y_test, y_pred, zero_division=0)
    rapor = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    print(f"  Holdout accuracy: {holdout_acc:.3f}")
    print(f"  Holdout F1      : {holdout_f1:.3f}")
    if onceki_accuracy:
        fark = kazanan_cv["mean"] - onceki_accuracy
        isaret = "+" if fark >= 0 else ""
        print(f"  Önceki cv_f1   : {onceki_accuracy:.3f} ({isaret}{fark:.3f})")

    # Kazananı tüm veriyle yeniden fit et (daha sağlam tahmin için)
    kazanan.fit(X, y)

    # Feature importance / katsayı
    feature_names = FEATURES + [f"sehir_{f}" for f in FEATURES]
    if hasattr(kazanan, "coef_"):
        agirlik = kazanan.coef_[0]
    elif hasattr(kazanan, "feature_importances_"):
        agirlik = kazanan.feature_importances_
    else:
        agirlik = np.zeros(len(feature_names))

    importance = pd.DataFrame({
        "feature": feature_names,
        "katsayi": agirlik,
        "abs_katsayi": np.abs(agirlik),
    }).sort_values("abs_katsayi", ascending=False)

    print("\n  En etkili 5 feature:")
    for _, row in importance.head(5).iterrows():
        yon = "+" if row["katsayi"] > 0 else "-"
        print(f"    {yon} {row['feature']}: {row['abs_katsayi']:.3f}")

    _grafik_kaydet(importance, y_test, y_pred, kazanan_cv["mean"], kazanan_ad)

    sonuclar = {
        "model": kazanan_ad,
        "f1": round(kazanan_cv["mean"], 4),             # cv_mean
        "cv_std":   round(kazanan_cv["std"], 4),
        "cv_k":     kazanan_cv["k"],
        "holdout_accuracy": round(holdout_acc, 4),
        "holdout_f1": round(holdout_f1, 4),
        "veri_sayisi": n,
        "tum_modeller": cv_sonuc,
        "rapor": rapor,
        "feature_importance": importance.head(10).to_dict("records"),
    }
    with open(SONUC_PATH, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)

    return kazanan, kazanan_cv["mean"]


def _grafik_kaydet(importance, y_test, y_pred, cv_f1, model_ad):
    grafik_dir = os.path.join(os.path.dirname(__file__), "..", "app", "static")
    os.makedirs(grafik_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    top10 = importance.head(10)
    renkler = ["#2ecc71" if k > 0 else "#e74c3c" for k in top10["katsayi"]]
    axes[0].barh(top10["feature"], top10["abs_katsayi"], color=renkler)
    axes[0].set_title(f"Feature Önemi ({model_ad})", fontsize=13)
    axes[0].set_xlabel("Mutlak Katsayı / Importance")
    axes[0].invert_yaxis()

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Beğenmedi", "Beğendi"])
    disp.plot(ax=axes[1], colorbar=False)
    axes[1].set_title(f"Confusion Matrix (CV F1: {cv_f1:.2%})", fontsize=13)

    plt.tight_layout()
    plt.savefig(os.path.join(grafik_dir, "model_analiz.png"), dpi=150)
    plt.close()
    print("  Grafik: app/static/model_analiz.png")


def model_kaydet(model):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"  Model kaydedildi: {MODEL_PATH}")


def onceki_accuracy_yukle():
    if os.path.exists(SONUC_PATH):
        with open(SONUC_PATH, "r") as f:
            data = json.load(f)
            return data.get("f1", data.get("accuracy"))
    return None


def main():
    print("[Eğitim] Veri yükleniyor...")
    try:
        X, y = veri_yukle()
    except FileNotFoundError:
        print("[Eğitim] kullanici_veri.csv bulunamadı.")
        return

    onceki = onceki_accuracy_yukle()
    model, acc = model_egit(X, y, onceki)
    if model is not None:
        model_kaydet(model)


if __name__ == "__main__":
    main()
