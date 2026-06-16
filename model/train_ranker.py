"""Train city ranker from session pairwise data.

Usage:
    python -m model.train_ranker            # train and promote if gate passes
    python -m model.train_ranker --dry-run  # evaluate only, no file writes
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

DATA_DIR = Path(__file__).parent.parent / "data"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
RANKER_PATH = ARTIFACTS_DIR / "city_ranker.joblib"
EVAL_HISTORY_PATH = ARTIFACTS_DIR / "eval_history.json"

MIN_SESSIONS_LR = 30
MIN_SESSIONS_LGBM = 200


def _load_pairs() -> pd.DataFrame | None:
    pairs_path = DATA_DIR / "training_pairs.parquet"
    if not pairs_path.exists():
        return None
    return pd.read_parquet(pairs_path)


def _load_eval_history() -> list[dict]:
    if not EVAL_HISTORY_PATH.exists():
        return []
    with open(EVAL_HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _append_eval(entry: dict) -> None:
    history = _load_eval_history()
    history.append(entry)
    EVAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _best_score(history: list[dict]) -> tuple[float, float]:
    if not history:
        return 0.0, 0.1
    best = max(history, key=lambda h: h.get("score", 0.0))
    return float(best.get("score", 0.0)), float(best.get("std", 0.1))


def train(dry_run: bool = False) -> None:
    df = _load_pairs()
    if df is None or df.empty:
        print("[SKIP] No training pairs. Run: python scripts/build_training_pairs.py")
        return

    n_sessions = df["session_id"].nunique()
    print(f"[INFO] {n_sessions} sessions, {len(df)} pairs")

    if n_sessions < MIN_SESSIONS_LR:
        print(f"[SKIP] Need >= {MIN_SESSIONS_LR} sessions (have {n_sessions}). Using cosine fallback.")
        return

    X = np.array(df["features"].tolist(), dtype=np.float32)
    y = df["label"].values.astype(int)

    if n_sessions >= MIN_SESSIONS_LGBM:
        try:
            import lightgbm as lgb
            model = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05,
                                        num_leaves=31, random_state=42, verbose=-1)
            ranker_type = "lgbm"
        except ImportError:
            model = LogisticRegression(max_iter=500, random_state=42)
            ranker_type = "lr"
    else:
        model = LogisticRegression(max_iter=500, random_state=42)
        ranker_type = "lr"

    cv_folds = min(5, n_sessions)
    scores = cross_val_score(model, X, y, cv=cv_folds, scoring="roc_auc")
    score_mean = float(scores.mean())
    score_std = float(scores.std())
    print(f"[EVAL] {ranker_type} CV ROC-AUC: {score_mean:.3f} ± {score_std:.3f} ({cv_folds}-fold)")

    best, best_std = _best_score(_load_eval_history())
    if score_mean < best - 0.5 * best_std:
        print(f"[SKIP] Score {score_mean:.3f} < best {best:.3f} − 0.5σ ({best - 0.5*best_std:.3f}). Not promoting.")
        return

    if dry_run:
        print(f"[DRY-RUN] Would promote {ranker_type} model (score={score_mean:.3f}). No files written.")
        return

    model.fit(X, y)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, RANKER_PATH)
    print(f"[OK] Model promoted → {RANKER_PATH}")

    # Update version.py RANKER_VERSION
    version_path = Path(__file__).parent / "version.py"
    if version_path.exists():
        text = version_path.read_text(encoding="utf-8")
        import re
        text = re.sub(r'RANKER_VERSION\s*=\s*"[^"]*"', f'RANKER_VERSION = "{ranker_type}"', text)
        version_path.write_text(text, encoding="utf-8")

    _append_eval({
        "date": datetime.date.today().isoformat(),
        "ranker": ranker_type,
        "n_sessions": n_sessions,
        "n_pairs": len(df),
        "score": score_mean,
        "std": score_std,
    })
    print(f"[OK] Eval history → {EVAL_HISTORY_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train city ranker from session pairwise data.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate only, no file writes.")
    args = parser.parse_args()
    train(dry_run=args.dry_run)
