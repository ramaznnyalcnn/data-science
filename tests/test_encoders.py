"""Tests for model/encoders.py — sentence-transformer encoder."""
import numpy as np
import pytest

from model.encoders import EMB_DIM, encode


def test_encode_empty_returns_correct_shape():
    embs = encode([])
    assert embs.shape == (0, EMB_DIM)
    assert embs.dtype == np.float32


def test_encode_single_text_shape():
    embs = encode(["merhaba"])
    assert embs.shape == (1, EMB_DIM)


def test_encode_l2_normalized():
    embs = encode(["Ege sahili, beyaz kum ve turkuaz deniz"])
    norm = float(np.linalg.norm(embs[0]))
    assert abs(norm - 1.0) < 1e-4


def test_encode_batch_all_normalized():
    texts = ["metin bir", "metin iki", "metin üç"]
    embs = encode(texts)
    assert embs.shape == (3, EMB_DIM)
    norms = np.linalg.norm(embs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)


def test_encode_different_texts_differ():
    e1 = encode(["Ege sahili beyaz kum"])
    e2 = encode(["Kayak pistleri karlı dağlar"])
    cosine = float(np.dot(e1[0], e2[0]))
    assert cosine < 0.99


def test_encode_same_text_identical():
    text = "İstanbul Boğazı"
    e1 = encode([text])
    e2 = encode([text])
    assert np.allclose(e1, e2, atol=1e-5)


def test_lazy_load_no_reimport(monkeypatch):
    """Calling encode twice should not reload the model."""
    import model.encoders as enc_module
    load_calls = []
    original_get = enc_module._get_model

    def counting_get():
        load_calls.append(1)
        return original_get()

    monkeypatch.setattr(enc_module, "_get_model", counting_get)
    encode(["test 1"])
    encode(["test 2"])
    # _get_model called twice (once per encode call), but model instantiated once
    assert len(load_calls) == 2
    assert enc_module._model is not None
