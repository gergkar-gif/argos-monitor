import math
import sqlite3
import unittest
import numpy as np

from argos import rank
from argos.cluster import _pick_representative


class TestRankAndRepresentative(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE source (id TEXT PRIMARY KEY, name TEXT, scope TEXT, kind TEXT);
        CREATE TABLE article (
            id INTEGER PRIMARY KEY, source_id TEXT, syndicated_of INTEGER,
            title TEXT, published_at TEXT, fetched_at TEXT
        );
        CREATE TABLE story (
            id INTEGER PRIMARY KEY, score REAL, policy REAL, themes TEXT
        );
        CREATE TABLE story_article (
            story_id INTEGER, article_id INTEGER, similarity REAL DEFAULT 1.0
        );
        """)

    def test_multi_outlet_consensus_beats_single_tagged_fluff(self):
        """A 5-outlet consensus national story must outrank a 1-outlet mis-tagged item."""
        # Insert sources
        for i in range(1, 10):
            self.db.execute("INSERT INTO source VALUES (?, ?, 'domestic', 'paper')", (f"src_{i}", f"Source {i}"))
        self.db.execute("INSERT INTO source VALUES ('fluff_src', 'Fluff Outlet', 'international', 'portal')")

        # Story 1: 1-outlet article with accidental policy 1.0 (e.g. matched 'investment')
        self.db.execute("INSERT INTO article VALUES (1, 'fluff_src', NULL, 'Stock market PhDs', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')")
        self.db.execute("INSERT INTO story VALUES (1, NULL, 1.0, 'investment')")
        self.db.execute("INSERT INTO story_article VALUES (1, 1, 1.0)")

        # Story 2: 5 independent domestic outlets with NO theme (policy 0.3)
        self.db.execute("INSERT INTO story VALUES (2, NULL, 0.3, NULL)")
        for i in range(1, 6):
            self.db.execute("INSERT INTO article VALUES (?, ?, NULL, 'Major national event', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')", (10 + i, f"src_{i}"))
            self.db.execute("INSERT INTO story_article VALUES (2, ?, 1.0)", (10 + i,))

        # Run rank
        rank.run(self.db)

        score_1 = self.db.execute("SELECT score FROM story WHERE id=1").fetchone()[0]
        score_2 = self.db.execute("SELECT score FROM story WHERE id=2").fetchone()[0]

        # Multi-outlet consensus (5 outlets) MUST beat 1-outlet tagged fluff
        self.assertGreater(score_2, score_1, f"5-outlet consensus ({score_2}) should beat 1-outlet tagged item ({score_1})")

    def test_standing_rule_8_elections_priority(self):
        """Elections must receive top policy priority and priority coverage boost."""
        self.db.execute("INSERT INTO source VALUES ('src_a', 'Outlet A', 'domestic', 'paper')")
        self.db.execute("INSERT INTO source VALUES ('src_b', 'Outlet B', 'domestic', 'paper')")

        # Story 1: 2-outlet election story
        self.db.execute("INSERT INTO story VALUES (1, NULL, 1.0, 'elections, party_gov')")
        self.db.execute("INSERT INTO article VALUES (1, 'src_a', NULL, 'Presidential election results', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')")
        self.db.execute("INSERT INTO article VALUES (2, 'src_b', NULL, 'Voter turnout surges', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')")
        self.db.execute("INSERT INTO story_article VALUES (1, 1, 1.0)")
        self.db.execute("INSERT INTO story_article VALUES (1, 2, 1.0)")

        # Story 2: 2-outlet regular policy story (trade)
        self.db.execute("INSERT INTO story VALUES (2, NULL, 1.0, 'trade')")
        self.db.execute("INSERT INTO article VALUES (3, 'src_a', NULL, 'New bilateral tariff rates', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')")
        self.db.execute("INSERT INTO article VALUES (4, 'src_b', NULL, 'Customs policy update', '2026-11-12T10:00:00Z', '2026-11-12T10:00:00Z')")
        self.db.execute("INSERT INTO story_article VALUES (2, 3, 1.0)")
        self.db.execute("INSERT INTO story_article VALUES (2, 4, 1.0)")

        rank.run(self.db)
        score_elec = self.db.execute("SELECT score FROM story WHERE id=1").fetchone()[0]
        score_trade = self.db.execute("SELECT score FROM story WHERE id=2").fetchone()[0]

        self.assertGreater(score_elec, score_trade)
        self.assertAlmostEqual(score_elec - score_trade, 2.5, places=1)

    def test_pick_representative_penalizes_opinion_and_syndication(self):
        """Authoritative domestic newspaper of record must be chosen over foreign op-ed."""
        # Setup 3 articles
        # idx 0: Foreign opinion piece close to centroid
        # idx 1: Domestic paper of record
        # idx 2: Domestic syndicated wire copy
        centroid = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        X = np.array([
            [0.99, 0.1, 0.0],  # very close to centroid
            [0.95, 0.2, 0.0],  # slightly lower similarity
            [0.96, 0.1, 0.0],
        ], dtype=np.float32)
        # Normalize rows
        X /= np.linalg.norm(X, axis=1, keepdims=True)

        rows = [
            {
                "id": 101,
                "title": "Opinion: The election turning point",
                "scope": "international",
                "kind": "media",
                "syndicated_of": None,
            },
            {
                "id": 102,
                "title": "Official ballot results certified by electoral court",
                "scope": "domestic",
                "kind": "paper",
                "syndicated_of": None,
            },
            {
                "id": 103,
                "title": "Official ballot results certified by electoral court",
                "scope": "domestic",
                "kind": "paper",
                "syndicated_of": 102,
            },
        ]

        rep = _pick_representative(rows, X, [0, 1, 2], centroid)
        self.assertEqual(rep, 1, "Domestic newspaper of record (idx 1) must be selected over foreign opinion (idx 0)")


if __name__ == "__main__":
    unittest.main()
