"""
Anonim session logger.

Her session bir JSON satırı olarak `data/sessions.jsonl`'e atomic append'lenir.
İsim/email/IP gibi PII alanları yazılmaz.

Kullanım:
    sl = SessionLogger()
    sl.start(scope={...})
    sl.log_photo_turn(shown_pair=..., picked=..., posterior=[...])
    sl.log_region_pick(shown_top3=[...], picked=[...])
    sl.log_context(method="nlp"|"preset"|"skip", ...)
    sl.log_survey(asked_qids, skipped_qids, skip_reason, answers, vector_delta)
    sl.log_stage2(candidate_pool, ranked_backend, shown_order, click_position, user_pick, time_to_pick_s)
    sl.log_feedback(satisfaction, would_book, comment, alt_pick)
    sl.flush()
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from model.encoders import MODEL_NAME
from model.file_lock import exclusive_file_lock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SESSIONS_PATH = os.path.join(ROOT, "data", "sessions.jsonl")

PIPELINE_VERSION = "v0.3"
PRESET_SET_VERSION = "v1"
ENCODER_NAME = MODEL_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SessionLogger:
    def __init__(self, path: str = SESSIONS_PATH):
        self.path = path
        self.session_id: Optional[str] = None
        self.ts_start: Optional[str] = None
        self.payload: dict[str, Any] = {}

    # ── lifecycle ─────────────────────────────────────────────────────────
    def start(self, scope: dict) -> str:
        self.session_id = str(uuid.uuid4())
        self.ts_start = _now_iso()
        self.payload = {
            "session_id": self.session_id,
            "ts_start": self.ts_start,
            "scope": scope,
            "stage1_photos": {
                "shown_pairs": [],
                "picks": [],
                "posterior_after_each_turn": [],
                "stop_reason": None,
                "turn_count": 0,
            },
            "stage1_5_region_pick": {
                "shown_top3": [],
                "picked": [],
                "none_fallback_count": 0,
            },
            "stage_context": {"method": None},
            "stage_survey": {
                "asked_qids": [],
                "skipped_qids": [],
                "skip_reason": {},
                "answers": {},
                "pairwise_turns": [],
                "answer_vector_delta": {},
            },
            "stage2_cities": {},
            "stage3_feedback": {},
            "model_versions": {
                "encoder": ENCODER_NAME,
                "predict_pipeline": PIPELINE_VERSION,
                "preset_set": PRESET_SET_VERSION,
            },
        }
        return self.session_id

    # ── stage logging ─────────────────────────────────────────────────────
    def log_photo_turn(
        self, shown_pair: tuple[str, str], picked: str, posterior: list[float]
    ) -> None:
        s = self.payload["stage1_photos"]
        s["shown_pairs"].append(list(shown_pair))
        s["picks"].append(picked)
        s["posterior_after_each_turn"].append([round(float(x), 4) for x in posterior])
        s["turn_count"] += 1

    def finish_photos(self, stop_reason: str) -> None:
        self.payload["stage1_photos"]["stop_reason"] = stop_reason

    def log_region_pick(
        self, shown_top3: list[str], picked: list[str], none_fallback_count: int = 0
    ) -> None:
        self.payload["stage1_5_region_pick"] = {
            "shown_top3": list(shown_top3),
            "picked": list(picked),
            "none_fallback_count": int(none_fallback_count),
        }

    def log_context(
        self,
        method: str,
        nlp_text: Optional[str] = None,
        nlp_top_regions: Optional[list] = None,
        nlp_top_presets: Optional[list] = None,
        preset_picks: Optional[list[str]] = None,
        partial_fizik: Optional[list] = None,
        partial_sosyal: Optional[list] = None,
        confidence: float = 0.0,
    ) -> None:
        self.payload["stage_context"] = {
            "method": method,
            "nlp_text": nlp_text,
            "nlp_text_len": len(nlp_text) if nlp_text else 0,
            "nlp_top_regions": nlp_top_regions or [],
            "nlp_top_presets": nlp_top_presets or [],
            "preset_picks": preset_picks or [],
            "partial_fizik": _clean_partial(partial_fizik),
            "partial_sosyal": _clean_partial(partial_sosyal),
            "confidence": round(float(confidence), 3),
        }

    def log_survey(
        self,
        asked_qids: list[str],
        skipped_qids: list[str],
        skip_reason: dict,
        answers: dict,
        answer_vector_delta: dict,
        pairwise_turns: Optional[list[dict]] = None,
    ) -> None:
        self.payload["stage_survey"] = {
            "asked_qids": list(asked_qids),
            "skipped_qids": list(skipped_qids),
            "skip_reason": dict(skip_reason),
            "answers": dict(answers),
            "pairwise_turns": pairwise_turns or [],
            "answer_vector_delta": {k: round(float(v), 3) for k, v in answer_vector_delta.items()},
        }

    def log_stage2(
        self,
        candidate_pool: list[str],
        ranked_backend: list[tuple[str, float]],
        shown_order: list[str],
        click_position: Optional[int],
        user_pick: Optional[str],
        time_to_pick_s: Optional[float],
    ) -> None:
        ranked_names = [city for city, _ in ranked_backend]
        rank_position = ranked_names.index(user_pick) if user_pick in ranked_names else None
        shown_position = shown_order.index(user_pick) if user_pick in shown_order else None
        self.payload["stage2_cities"] = {
            "candidate_pool": list(candidate_pool),
            "ranked_backend": [[c, round(float(s), 4)] for c, s in ranked_backend],
            "shown_order": list(shown_order),
            "click_position": click_position,
            "rank_position": rank_position,
            "shown_position": shown_position,
            "user_pick": user_pick,
            "time_to_pick_s": round(float(time_to_pick_s), 1) if time_to_pick_s is not None else None,
        }

    def log_feedback(
        self,
        satisfaction: str,
        would_book: Optional[bool] = None,
        comment: str = "",
        alt_pick: Optional[str] = None,
    ) -> None:
        self.payload["stage3_feedback"] = {
            "satisfaction": satisfaction,
            "would_book": would_book,
            "comment": (comment or "").strip()[:500],
            "alt_pick": alt_pick,
        }

    # ── persist ───────────────────────────────────────────────────────────
    def flush(self) -> None:
        if not self.session_id:
            return
        ts_end = _now_iso()
        self.payload["ts_end"] = ts_end
        if self.ts_start:
            t0 = datetime.strptime(self.ts_start, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            t1 = datetime.strptime(ts_end, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            self.payload["duration_s"] = int((t1 - t0).total_seconds())

        line = json.dumps(self.payload, ensure_ascii=False, default=str)
        with exclusive_file_lock(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


def _clean_partial(arr) -> Optional[list]:
    if arr is None:
        return None
    out = []
    for v in arr:
        try:
            f = float(v)
            out.append(None if f != f else round(f, 3))  # NaN check
        except (TypeError, ValueError):
            out.append(None)
    return out
