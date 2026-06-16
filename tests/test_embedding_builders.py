"""Tests for embedding builder scripts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def test_photo_embedding_builder_covers_categories_and_tours(monkeypatch, tmp_path):
    import scripts.build_photo_embeddings as builder

    data = {
        "kategoriler": [
            {
                "sol": {"dosya": "k1_sol.jpg", "aciklama": "sahil"},
                "sag": {"dosya": "k1_sag.jpg", "aciklama": "dag"},
            }
        ],
        "turlar": [
            {
                "sol": {"dosya": "tur1_sol.jpg", "aciklama": "hareketli"},
                "sag": {"dosya": "tur1_sag.jpg", "aciklama": "sakin"},
            }
        ],
    }
    data_path = tmp_path / "fotograflar.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "embeddings"

    def fake_encode(texts):
        rows = []
        for i, _ in enumerate(texts, start=1):
            vec = np.zeros(384, dtype=np.float32)
            vec[0] = float(i)
            rows.append(vec)
        return np.array(rows, dtype=np.float32)

    monkeypatch.setattr(builder, "DATA_PATH", data_path)
    monkeypatch.setattr(builder, "OUT_DIR", out_dir)
    monkeypatch.setattr("model.encoders.encode", fake_encode)

    assert builder.main() == 0
    assert sorted(path.name for path in out_dir.glob("photo_*.npy")) == [
        "photo_k1_sag.npy",
        "photo_k1_sol.npy",
        "photo_tur1_sag.npy",
        "photo_tur1_sol.npy",
    ]


def test_context_embedding_builder_writes_contexts_and_regions(monkeypatch, tmp_path):
    import scripts.build_context_embeddings as builder

    presets_path = tmp_path / "context_presets.json"
    regions_path = tmp_path / "regions.json"
    out_dir = tmp_path / "embeddings"
    presets_path.write_text(
        json.dumps({"presets": [{"id": "p1", "text": "deniz"}, {"id": "p2", "text": "dag"}]}),
        encoding="utf-8",
    )
    regions_path.write_text(
        json.dumps([
            {"id": "r1", "hidden_description": "sahil", "open_description": "kiyi"},
            {"id": "r2", "hidden_description": "orman", "open_description": "yayla"},
        ]),
        encoding="utf-8",
    )

    def fake_encode(texts):
        rows = []
        for i, _ in enumerate(texts, start=1):
            vec = np.zeros(384, dtype=np.float32)
            vec[i] = 1.0
            rows.append(vec)
        return np.array(rows, dtype=np.float32)

    monkeypatch.setattr(builder, "PRESETS_PATH", presets_path)
    monkeypatch.setattr(builder, "REGIONS_PATH", regions_path)
    monkeypatch.setattr(builder, "OUT_DIR", out_dir)
    monkeypatch.setattr("model.encoders.encode", fake_encode)

    assert builder.main() == 0
    contexts = np.load(out_dir / "contexts.npz")
    regions = np.load(out_dir / "regions.npz")
    assert list(contexts["ids"]) == ["p1", "p2"]
    assert contexts["embeddings"].shape == (2, 384)
    assert list(regions["ids"]) == ["r1", "r2"]
    assert regions["embeddings"].shape == (2, 384)
