"""Tests for embedder empty guards and policy theme prototype fallbacks."""
import unittest
import sys
import pathlib
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.embed import DIM, Embedder
from argos import packs


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

    def test_all_country_packs_have_valid_theme_prototypes(self):
        """Ensure all 87 country packs define themes with non-empty labels or descriptions."""
        pack_list = packs.pack_ids()
        self.assertGreater(len(pack_list), 0, "At least one country pack should exist")
        for cid in pack_list:
            cfg = packs.load(cid).get("themes") or {}
            themes = cfg.get("themes") or []
            self.assertGreater(len(themes), 0, f"Pack {cid} must have themes defined")
            for t in themes:
                tid = t.get("id")
                self.assertTrue(tid, f"Theme in pack {cid} missing id")
                self.assertTrue(t.get("label"), f"Theme {tid} in pack {cid} missing label")
                desc = t.get("describe") or [t.get("label")]
                self.assertTrue(desc and any(d and str(d).strip() for d in desc),
                                f"Theme {tid} in pack {cid} must have non-empty describe or label")


if __name__ == "__main__":
    unittest.main()
