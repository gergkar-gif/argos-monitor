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

    def test_cross_country_not_syndicated(self):
        self.db.execute("ALTER TABLE article ADD COLUMN country TEXT")
        body = ("Brussels - European Union energy ministers convened on Tuesday to finalize "
                "cross-border electricity interconnectors and winter gas storage obligations. "
                "The council adopted binding regional solidarity rules across all member states.")
        self.db.execute("INSERT INTO source VALUES ('reuters', 'Reuters', 'wire', 0, 0)")
        self.db.execute("INSERT INTO source VALUES ('politico', 'Politico Europe', 'media', 0, 0)")
        self.db.execute("INSERT INTO article (id, country, source_id, title, text, published_at) "
                        "VALUES (20, 'hungary', 'reuters', 'EU ministers finalize energy solidarity rules', ?, '2026-11-10T08:00:00Z')", (body,))
        self.db.execute("INSERT INTO article (id, country, source_id, title, text, published_at) "
                        "VALUES (21, 'romania', 'politico', 'EU ministers finalize energy solidarity rules', ?, '2026-11-10T08:15:00Z')", (body,))

        normalise.run(self.db)
        r21 = self.db.execute("SELECT syndicated_of FROM article WHERE id=21").fetchone()
        self.assertIsNone(r21["syndicated_of"], "Articles on different country desks must not be marked syndicated_of across countries")

    def test_cjk_wire_reprint_marked_syndicated(self):
        wire_body = (
            "新华社北京11月17日电 中国外交部发言人17日在例行记者会上表示，中方一贯秉持相互尊重、"
            "和平共处、合作共赢原则处理中美关系，推动亚太经合组织深圳峰会取得务实合作成果。"
            "发言人强调，各国应当共同维护多边贸易体制与全球产业链供应链稳定畅通。"
        )
        self.db.execute("INSERT INTO source VALUES ('xinhua', 'Xinhua', 'official', 1, 0)")
        self.db.execute("INSERT INTO source VALUES ('portal', 'Sohu', 'media', 0, 0)")
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (30, 'xinhua', '外交部回应深圳APEC合作', ?, '2026-11-17T08:00:00Z')", (wire_body,))
        reprint = "据新华社报道，" + wire_body
        self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) "
                        "VALUES (31, 'portal', '中方回应亚太经合组织峰会', ?, '2026-11-17T08:20:00Z')", (reprint,))

        normalise.run(self.db)
        r31 = self.db.execute("SELECT syndicated_of FROM article WHERE id=31").fetchone()
        self.assertEqual(r31["syndicated_of"], 30, "Chinese Xinhua reprint must be marked as syndicated")

    def test_central_european_wire_reprint_marked_syndicated(self):
        cases = [
            ("dpa", "dpa", "(dpa) ", "Berlin, Germany - The federal cabinet approved new infrastructure spending across rail corridors, electricity grids, and industrial competitiveness measures on Tuesday after weeks of coalition budget negotiations in the Bundestag and Bundesrat committees."),
            ("apa", "APA", "laut APA ", "Wien - Der Nationalrat hat am Dienstag das Budgetsanierungspaket sowie neue Investitionen in die Schieneninfrastruktur, Energieversorgung und Landesverteidigung nach intensiven Ausschussberatungen mit klarer Mehrheit im Hohen Haus beschlossen."),
            ("pap", "PAP", "(PAP) ", "Warszawa - Rząd przyjął we wtorek projekt ustawy budżetowej oraz wieloletni plan modernizacji energetyki jądrowej, sieci przesyłowych i umocnień na granicy wschodniej w ramach programu Tarcza Wschód po konsultacjach resortowych."),
            ("ctk", "ČTK", "podle ČTK ", "Praha - Vláda v úterý schválila rozpočtový rámec a podporu pro dostavbu nových bloků jaderné elektrárny Dukovany i modernizaci vysokorychlostních železničních koridorů napříč Českou republikou po jednání ministrů a zástupců průmyslu, energetiky a ministerstva financí v Poslanecké sněmovně."),
            ("mti", "MTI", "(MTI) ", "Budapest - Az Országgyűlés kedden elfogadta a jövő évi költségvetési törvényjavaslatot és a hazai energetikai hálózatfejlesztési beruházások kiemelt támogatását a gazdasági és pénzügyi bizottság jóváhagyását követően."),
            ("tasr", "TASR", "(TASR) ", "Bratislava - Vláda v utorok schválila konsolidačný balík verejných financií a opatrenia pre energetickú bezpečnosť, tranzit plynu cez územie Slovenska a podporu domáceho automobilového priemyslu na rokovaní kabinetu."),
            ("sta", "STA", "(STA) ", "Ljubljana - Vlada je v torek potrdila proračunski načrt za prihodnje leto ter strateške ukrepe za širitev pristanišča Luka Koper, gradnjo drugega tira in priprave na energetski projekt JEK2 v Posavju."),
            ("hina", "HINA", "izvještava HINA ", "Zagreb - Vlada je u utorak donijela paket mjera za energetsku sigurnost preko terminala na Krku i naftovoda JANAF te odobrila nova ulaganja u željezničku infrastrukturu prema luci Rijeka."),
        ]
        for idx, (sid, sname, marker, body) in enumerate(cases, start=40):
            wire_id = idx * 10
            rep_id = wire_id + 1
            rep_sid = f"paper_{sid}"
            self.db.execute("INSERT INTO source VALUES (?, ?, 'wire', 1, 0)", (sid, sname))
            self.db.execute("INSERT INTO source VALUES (?, ?, 'media', 0, 0)", (rep_sid, f"Daily {sname}"))
            self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) VALUES (?, ?, 'Wire headline', ?, '2026-11-25T08:00:00Z')", (wire_id, sid, body))
            reprint = f"{marker}{body} Regional commentators added brief local context regarding parliamentary timetable."
            self.db.execute("INSERT INTO article (id, source_id, title, text, published_at) VALUES (?, ?, 'Paper headline', ?, '2026-11-25T08:25:00Z')", (rep_id, rep_sid, reprint))

        normalise.run(self.db)
        for idx, (sid, _, _, _) in enumerate(cases, start=40):
            r = self.db.execute("SELECT syndicated_of FROM article WHERE id=?", (idx * 10 + 1,)).fetchone()
            self.assertEqual(r["syndicated_of"], idx * 10, f"Central European wire reprint for {sid} must be marked as syndicated")


if __name__ == "__main__":
    unittest.main()
