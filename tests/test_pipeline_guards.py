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


if __name__ == "__main__":
    unittest.main()
