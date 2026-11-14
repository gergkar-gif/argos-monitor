import sqlite3
import unittest
from unittest.mock import patch

from argos import excerpts, extract, reddit
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


if __name__ == "__main__":
    unittest.main()
