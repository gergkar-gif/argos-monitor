"""Tests for embedder empty guards and policy theme prototype fallbacks."""
import unittest
import sys
import pathlib
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.embed import DIM, Embedder


class TestEmbedPolicy(unittest.TestCase):
    def test_encode_empty_texts(self):
        emb = Embedder()
        res = emb.encode([])
        self.assertEqual(res.shape, (0, DIM))
        self.assertEqual(res.dtype, np.float32)

    def test_theme_describe_fallback(self):
        emb = Embedder()
        theme = {"id": "test_theme", "label": "AUKUS Defense Deterrence", "describe": []}
        desc = theme.get("describe") or [theme["label"]]
        self.assertEqual(desc, ["AUKUS Defense Deterrence"])
        vecs = emb.encode(["passage: " + d for d in desc])
        self.assertEqual(vecs.shape, (1, DIM))
        proto = vecs.mean(0)
        proto /= np.linalg.norm(proto)
        self.assertEqual(proto.shape, (DIM,))
        self.assertFalse(np.isnan(proto).any())


if __name__ == "__main__":
    unittest.main()
