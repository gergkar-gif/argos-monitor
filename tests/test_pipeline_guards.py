import sqlite3
import unittest
from unittest.mock import patch

from argos import excerpts, extract, packs, ratings, reddit
from argos.db import SCHEMA


class TestPipelineGuards(unittest.TestCase):
    def test_verify_detects_excerpt_mismatch(self):
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        db.execute(
            "INSERT INTO article (id, source_id, url, title, text) VALUES (1, 's1', 'https://example.com/1', 'T', 'Hello world from Hanoi.')"
        )
        db.execute("INSERT INTO story (id, country, window_days) VALUES (1, 'vietnam', 7)")
        db.execute(
            "INSERT INTO excerpt (id, story_id, article_id, text, char_start, char_end) VALUES (1, 1, 1, 'Hello world', 0, 11)"
        )
        self.assertTrue(excerpts.verify(db))

        db.execute("UPDATE excerpt SET text='Tampered text' WHERE id=1")
        self.assertFalse(excerpts.verify(db))

    def test_reddit_post_strips_emojis_and_normalises(self):
        post = reddit._post({
            "title": "🚨 Breaking Ha\u0300 No\u0302\u0323i news",
            "summary": "<p>Update 🔥</p> submitted by /u/test",
            "link": "https://www.reddit.com/r/VietNam/comments/abc/test/",
        })
        self.assertEqual(post["title"], "Breaking Hà Nội news")
        self.assertEqual(post["body"], "Update")
        self.assertEqual(post["sub"], "VietNam")

    def test_robots_for_fails_closed_on_transient_errors(self):
        extract._robots.clear()
        with patch("argos.extract.get", return_value=(404, b"")):
            rp_404 = extract._robots_for("https://allowed.example")
        self.assertTrue(rp_404.can_fetch("ArgosMonitor", "https://allowed.example/news/1"))

        extract._robots.clear()
        with patch("argos.extract.get", return_value=(503, b"")):
            rp_503 = extract._robots_for("https://down.example")
        self.assertFalse(rp_503.can_fetch("ArgosMonitor", "https://down.example/news/1"))

    def test_select_pending_round_robin_across_countries(self):
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        # Country A (early IDs) has a high-scoring 2-article story; Country Z (higher IDs) has 5 single-article stories
        db.execute("INSERT INTO article (id, source_id, url, title, extract_status, country) VALUES (1, 's1', 'https://a.example/1', 'A1', 'pending', 'algeria')")
        db.execute("INSERT INTO article (id, source_id, url, title, extract_status, country) VALUES (2, 's2', 'https://a.example/2', 'A2', 'pending', 'algeria')")
        db.execute("INSERT INTO story (id, country, window_days, score, representative_article_id) VALUES (1, 'algeria', 7, 15.0, 1)")
        db.execute("INSERT INTO story_article (story_id, article_id, similarity) VALUES (1, 1, 1.0), (1, 2, 0.95)")

        for i in range(10, 15):
            db.execute("INSERT INTO article (id, source_id, url, title, extract_status, country) VALUES (?, 'sz', ?, 'Z', 'pending', 'west_africa')", (i, f"https://z.example/{i}"))
            db.execute("INSERT INTO story (id, country, window_days, score, representative_article_id) VALUES (?, 'west_africa', 7, 1.0, ?)", (i, i))
            db.execute("INSERT INTO story_article (story_id, article_id, similarity) VALUES (?, ?, 1.0)", (i, i))

        picked = extract._select_pending(db, limit=2, story_only=True)
        self.assertEqual(len(picked), 2)
        self.assertEqual(picked[0]["id"], 1)
        self.assertEqual({r["id"] for r in picked}, {1, 14})

    def test_all_catalogued_sources_have_ratings(self):
        unrated = []
        for cid in packs.pack_ids():
            for s in packs.load(cid)["sources"]:
                r = ratings.lookup_rating(s.get("name", ""), bool(s.get("state_affiliated")), s.get("kind", "media"))
                if r["factuality"] == "unrated" or r["bias"] == "unrated":
                    unrated.append((cid, s.get("id"), s.get("name")))
        self.assertEqual(unrated, [], f"Unrated catalogued sources found: {unrated[:10]}")

    def test_all_desks_meet_independent_source_floors(self):
        from urllib.parse import urlparse
        cluster_floors = {
            "baltics": 15,
            "caribbean": 25,
            "central_america": 30,
            "east_africa": 30,
            "pacific_islands": 30,
            "west_africa": 30,
        }
        deficits = []
        for cid in packs.pack_ids():
            srcs = [s for s in packs.load(cid)["sources"] if not s.get("aggregator")]
            non_state = [
                s for s in srcs
                if not s.get("state_affiliated") and s.get("kind") != "official"
                and not s.get("reprints_vna") and not s.get("reprints_wire")
            ]
            doms = set()
            for s in non_state:
                d = urlparse(s.get("homepage") or "").netloc.lower().replace("www.", "")
                parts = d.split(".")
                if len(parts) > 2 and parts[0] in ("eng", "en", "rus", "ru", "fr", "es", "ar", "vi", "km", "news", "uz", "kz", "hy", "japannews", "english", "khmer"):
                    d = ".".join(parts[1:])
                doms.add(d or s["id"])
            floor = cluster_floors.get(cid, 10)
            if len(doms) < floor:
                deficits.append((cid, len(doms), floor))
        self.assertEqual(deficits, [], f"Desks below independent publisher floor: {deficits}")


if __name__ == "__main__":
    unittest.main()
