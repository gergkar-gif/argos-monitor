import unittest
import yaml
from argos import packs
from argos.config import COUNTRIES_DIR
from argos.packs import _term_regex


class TestPacks(unittest.TestCase):
    def test_term_regex_word_boundaries(self):
        """Spaced script terms must use word boundaries to prevent substring collisions."""
        import re

        # Substring false positives identified in audit must not match
        self.assertIsNone(re.search(_term_regex("lac"), "black place", re.I))
        self.assertIsNotNone(re.search(_term_regex("lac"), "LAC standoff", re.I))

        self.assertIsNone(re.search(_term_regex("modi"), "commodity trading", re.I))
        self.assertIsNotNone(re.search(_term_regex("modi"), "Narendra Modi speech", re.I))

        self.assertIsNone(re.search(_term_regex("rbi"), "Serbia election", re.I))
        self.assertIsNotNone(re.search(_term_regex("rbi"), "RBI governor announced", re.I))

        self.assertIsNone(re.search(_term_regex("mali"), "somalia normalisation", re.I))
        self.assertIsNotNone(re.search(_term_regex("mali"), "Bamako, Mali security", re.I))

        self.assertIsNone(re.search(_term_regex("niger"), "Nigeria oil output", re.I))
        self.assertIsNotNone(re.search(_term_regex("niger"), "Niamey, Niger junta", re.I))

        # Punctuation terms (e.g. Vietnamese city abbreviations)
        self.assertIsNotNone(re.search(_term_regex("tp.hcm"), "kinh tế tp.hcm khởi sắc", re.I))
        self.assertIsNone(re.search(_term_regex("tp.hcm"), "http.hcm.internal", re.I))

        # Unsegmented CJK script terms must still match inside contiguous text
        self.assertIsNotNone(re.search(_term_regex("北京"), "中国北京市", re.I))
        self.assertIsNotNone(re.search(_term_regex("東京"), "日本東京都", re.I))

    def test_all_packs_load_and_have_required_fields(self):
        """All 87 country packs must load cleanly and have standardized attributes."""
        cids = packs.pack_ids()
        self.assertGreaterEqual(len(cids), 87)
        for cid in cids:
            p = packs.load(cid)
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("mention_re", p)
            self.assertIsInstance(p["skip_sections"], set)
            self.assertIsInstance(p["foreign_sections"], set)
            self.assertIsInstance(p.get("reddit", []), list)

    def test_no_deprecated_top_level_keys(self):
        """No country pack.yaml may use deprecated bare top-level keys."""
        disallowed = {"skip_sections", "dateline", "subreddits"}
        for d in COUNTRIES_DIR.iterdir():
            pf = d / "pack.yaml"
            if not pf.exists():
                continue
            with open(pf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            present_disallowed = set(data.keys()) & disallowed
            self.assertEqual(
                present_disallowed,
                set(),
                f"{d.name}/pack.yaml contains deprecated keys: {present_disallowed}",
            )


if __name__ == "__main__":
    unittest.main()
