import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from argos import export


def _story(sid, category="internal_politics", score=5.0, outlets=3, last_24h=2, themes=None, delta=None):
    return {
        "id": sid,
        "category": category,
        "score": score,
        "independent_sources": outlets,
        "last_24h": last_24h,
        "themes": themes or [],
        "delta": delta,
        "headline": {"title": f"Headline {sid}", "url": f"https://example.com/{sid}", "source": "Test", "language": "en"},
        "excerpts": [],
        "sources": [],
    }


class HomeExportTests(unittest.TestCase):
    def test_pick_desk_lead_prefers_substantive_over_other(self):
        stories = [
            _story("s1", category="other", score=20.0),
            _story("s2", category="foreign_policy", score=8.0),
        ]
        self.assertEqual(export._pick_desk_lead(stories)["id"], "s2")
        self.assertEqual(export._pick_desk_lead([stories[0]])["id"], "s1")
        self.assertIsNone(export._pick_desk_lead([]))

    def test_home_exports_triage_counts_and_elections(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            d7 = {
                "totals": {"internal_politics": 1, "other": 1},
                "stories": [
                    _story("tabloid", category="other", score=15.0, outlets=5),
                    _story(
                        "vote",
                        category="internal_politics",
                        score=10.0,
                        outlets=4,
                        themes=["national elections and voting"],
                        delta={"state": "surging", "scope_shift": True},
                    ),
                ],
            }
            d24 = {"totals": {"internal_politics": 1}, "stories": [d7["stories"][1]]}
            (data_dir / "testland-7d.json").write_text(json.dumps(d7), encoding="utf8")
            (data_dir / "testland-24h.json").write_text(json.dumps(d24), encoding="utf8")

            with patch.object(export, "SITE_DATA", data_dir):
                home = export._home("2026-11-14T00:00:00+00:00", [{"id": "testland", "name": "Testland", "region": "Asia"}])

            self.assertEqual(len(home["desks"]), 1)
            desk = home["desks"][0]
            self.assertEqual(desk["lead"]["title"], "Headline vote")
            self.assertTrue(desk["lead"]["is_election"])
            self.assertEqual(desk["surging"], 1)
            self.assertEqual(desk["elections"], 1)
            self.assertEqual(desk["intl_pickups"], 1)
            self.assertEqual([s["id"] for s in home["elections"]], ["vote"])
            self.assertEqual(home["most_reported"][0]["id"], "vote")


if __name__ == "__main__":
    unittest.main()
