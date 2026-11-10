"""Tests for syndication detection and wire reprint deduplication (Rule 5)."""
import sqlite3
import unittest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos import normalise


class TestNormaliseSyndication(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE source (id TEXT PRIMARY KEY, name TEXT, kind TEXT, state_affiliated INTEGER, reprints_vna INTEGER);
        CREATE TABLE article (
            id INTEGER PRIMARY KEY, source_id TEXT, title TEXT, lead TEXT, text TEXT,
            published_at TEXT, content_hash TEXT, syndicated_of INTEGER, extract_status TEXT
        );
        """)

    def tearDown(self):
        self.db.close()

    def test_verbatim_reprint_marked(self):
        # Outlet A publishes wire dispatch
        body = ("Ha Noi, Vietnam - The National Assembly on Tuesday ratified the comprehensive "
                "economic partnership agreement with wide bipartisan majority. "
                "The vote passed with 450 delegates in favor, marking a historic milestone for trade. "
                "Officials emphasized that implementation begins immediately across all coastal ports.")
        self.db.execute("INSERT INTO source VALUES ('vna', 'Vietnam News Agency', 'wire', 1, 0)")
        self.db.execute("INSERT INTO source VALUES ('tuoitre', 'Tuoi Tre', 'media', 1, 0)")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (1, 'vna', 'NA ratifies trade pact', ?, '2026-11-10T08:00:00Z')", (body,))
        # Outlet B reprints almost identical text with minor header
        reprint = ("Tuoi Tre Online - " + body)
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (2, 'tuoitre', 'National Assembly passes trade agreement', ?, '2026-11-10T08:30:00Z')", (reprint,))

        normalise.run(self.db)
        r2 = self.db.execute("SELECT syndicated_of FROM article WHERE id=2").fetchone()
        self.assertEqual(r2["syndicated_of"], 1, "Reprint must be marked as syndicated of primary wire article")

    def test_distinct_article_not_syndicated(self):
        self.db.execute("INSERT INTO source VALUES ('vna', 'Vietnam News Agency', 'wire', 1, 0)")
        self.db.execute("INSERT INTO source VALUES ('bbc', 'BBC', 'media', 0, 0)")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (1, 'vna', 'NA ratifies trade pact', 'Story text about trade agreement.', '2026-11-10T08:00:00Z')")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (2, 'bbc', 'Typhoon makes landfall in central provinces', "
                        "'Severe meteorological disruption with gale force winds exceeding 120 km/h.', '2026-11-10T08:30:00Z')")

        normalise.run(self.db)
        r2 = self.db.execute("SELECT syndicated_of FROM article WHERE id=2").fetchone()
        self.assertIsNone(r2["syndicated_of"], "Unrelated story must not be marked as syndicated")

    def test_wire_credit_partial_overlap(self):
        # Outlet A is wire
        wire_body = ("Ha Noi, Vietnam - The Ministry of Industry and Trade announced new export quotas "
                     "for agricultural products starting from the second quarter of the fiscal year. "
                     "Key commodities include rice, coffee, and cashew nuts with designated tariff exemptions. "
                     "Customs checkpoints have received detailed regulatory guidelines.")
        self.db.execute("INSERT INTO source VALUES ('vna_wire', 'VNA Wire', 'wire', 1, 0)")
        self.db.execute("INSERT INTO source VALUES ('commercial_press', 'Commercial Daily', 'media', 0, 1)")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (10, 'vna_wire', 'Trade Ministry releases export quotas', ?, '2026-11-10T08:00:00Z')", (wire_body,))
        # Commercial outlet adds custom commentary but quotes wire and includes "(Theo TTXVN)"
        custom_wrapper = ("Theo TTXVN, Ministry of Industry and Trade announced new export quotas for agricultural products "
                          "starting from the second quarter of the fiscal year. Key commodities include rice, coffee, and cashew nuts. "
                          "Domestic market analysts believe this will bolster rural cooperative revenue significantly in coming months.")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (11, 'commercial_press', 'New agricultural quotas detailed', ?, '2026-11-10T08:35:00Z')", (custom_wrapper,))

        normalise.run(self.db)
        r11 = self.db.execute("SELECT syndicated_of FROM article WHERE id=11").fetchone()
        self.assertEqual(r11["syndicated_of"], 10, "Article crediting wire with partial overlap must be marked as syndicated")


if __name__ == "__main__":
    unittest.main()
