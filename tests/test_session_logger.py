"""Tests for model/session_logger.py."""

import json
import os
import tempfile

import pytest

from model.session_logger import SessionLogger
from model.encoders import MODEL_NAME


@pytest.fixture()
def tmp_path_logger(tmp_path):
    path = str(tmp_path / "sessions.jsonl")
    return SessionLogger(path=path)


def test_start_returns_session_id(tmp_path_logger):
    sid = tmp_path_logger.start(scope={"scope_mode": "karisik", "visa_mode": "vizesiz"})
    assert sid is not None
    assert len(sid) > 0


def test_flush_writes_line(tmp_path_logger):
    tmp_path_logger.start(scope={"scope_mode": "karisik"})
    tmp_path_logger.flush()
    assert os.path.exists(tmp_path_logger.path)
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1


def test_flushed_line_is_valid_json(tmp_path_logger):
    tmp_path_logger.start(scope={"scope_mode": "karisik"})
    tmp_path_logger.flush()
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert "session_id" in data
    assert "ts_start" in data
    assert "ts_end" in data


def test_flush_twice_appends_two_lines(tmp_path_logger):
    """Two separate sessions produce two JSONL lines."""
    path = tmp_path_logger.path
    logger2 = SessionLogger(path=path)

    tmp_path_logger.start(scope={"scope_mode": "turkiye"})
    tmp_path_logger.flush()

    logger2.start(scope={"scope_mode": "yurtdisi"})
    logger2.flush()

    with open(path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if l.strip()]
    assert len(lines) == 2


def test_schema_fields_present(tmp_path_logger):
    tmp_path_logger.start(scope={"scope_mode": "karisik"})
    tmp_path_logger.flush()
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    expected_keys = [
        "session_id", "ts_start", "ts_end", "scope",
        "stage1_photos", "stage1_5_region_pick",
        "stage_context", "stage_survey", "stage2_cities",
        "stage3_feedback", "model_versions",
    ]
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"


def test_encoder_metadata_matches_runtime_encoder(tmp_path_logger):
    tmp_path_logger.start(scope={"scope_mode": "karisik"})
    tmp_path_logger.flush()
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert data["model_versions"]["encoder"] == MODEL_NAME


def test_log_photo_turn_appends(tmp_path_logger):
    tmp_path_logger.start(scope={})
    tmp_path_logger.log_photo_turn(
        shown_pair=("foto1.jpg", "foto2.jpg"),
        picked="foto1.jpg",
        posterior=[0.6, 0.4],
    )
    tmp_path_logger.flush()
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert data["stage1_photos"]["turn_count"] == 1
    assert data["stage1_photos"]["picks"] == ["foto1.jpg"]


def test_log_stage2_keeps_ranked_and_shown_positions(tmp_path_logger):
    tmp_path_logger.start(scope={})
    tmp_path_logger.log_stage2(
        candidate_pool=["A", "B", "C"],
        ranked_backend=[("A", 0.9), ("B", 0.8), ("C", 0.7)],
        shown_order=["C", "A", "B"],
        click_position=2,
        user_pick="B",
        time_to_pick_s=4.3,
    )
    tmp_path_logger.flush()
    with open(tmp_path_logger.path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())

    stage2 = data["stage2_cities"]
    assert stage2["ranked_backend"] == [["A", 0.9], ["B", 0.8], ["C", 0.7]]
    assert stage2["shown_order"] == ["C", "A", "B"]
    assert stage2["rank_position"] == 1
    assert stage2["shown_position"] == 2
    assert stage2["click_position"] == 2


def test_no_flush_no_file(tmp_path):
    path = str(tmp_path / "no_flush.jsonl")
    logger = SessionLogger(path=path)
    logger.start(scope={})
    # Never flushed — file should not exist
    assert not os.path.exists(path)
