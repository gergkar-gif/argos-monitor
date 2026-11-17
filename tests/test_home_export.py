import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from argos import export, packs, policy, relevance, textutil


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

    def test_election_matcher_and_disaster_boundaries(self):
        m = policy._matcher(["scrutin", "elección", "választás"])
        self.assertFalse(m("govt mandates scrutiny of bids"))
        self.assertFalse(m("jugar contra la selección de costa rica"))
        self.assertFalse(m("a csapat kiválasztása"))
        self.assertTrue(m("second tour du scrutin présidentiel"))
        self.assertTrue(m("elección presidencial"))
        self.assertTrue(m("országgyűlési választásokon"))

        s_bahas = _story("id1")
        s_bahas["headline"]["title"] = "Prabowo Kumpulkan Ketum Parpol, Bahas Pengganti Gibran"
        self.assertIsNone(export._classify_disaster(s_bahas))

    def test_vietnam_election_false_positives_and_foreign_sections(self):
        packs.load.cache_clear()
        vn = packs.load("vietnam")
        elec = next(t for t in vn["themes"]["themes"] if t["id"] == "elections")
        self.assertEqual(
            policy._keyword_share([("fed sẽ không bỏ phiếu về lãi suất tại cuộc họp tháng 10 năm 2027", "")], elec["keywords"]),
            0.0,
        )
        self.assertGreater(
            policy._keyword_share([("bầu cử đại biểu quốc hội khóa xvi", "")], elec["keywords"]),
            0.0,
        )
        self.assertFalse(relevance.is_relevant(
            vn, "domestic", "general", "Tin mới nhất",
            "https://www.qdnd.vn/quoc-te/doi-song/chinh-sach-trung-dong-cua-my-sau-bau-cu-giua-nhiem-ky-1064548",
            "Chính sách Trung Đông của Mỹ sau bầu cử giữa nhiệm kỳ", "", "",
        ))

    def test_sports_stream_spam_rejected_and_real_news_kept(self):
        spam_cases = [
            ("!+!LIVE. France v Turkey Match LIVE Stream Tv Channel", "Universitat de Barcelona"),
            ("$#→ 【TRT1-CANLI+!】 Türkiye - Fransa maçı Canlı izle ! ** 15 Kasım 2026", "Universitat de Barcelona"),
            ("[MATCH!LIVE] Serbia v Germany LIVE Stream", "日本取引所グループ"),
            ("Greece vs Serbia prediction and betting tips 16 November 2026", "Dailysports"),
            ("EN VIVO: Guatemala vs Canadá por los Cuartos de Final de la CONCACAF Nations League", "TUDN"),
            ("Kazakhstan vs Slovakia: UEFA Nations League stats & head-to-head", "BBC"),
            ("Fransa-Türkiye maçı ne zaman, saat kaçta, hangi kanalda?", "Evrensel"),
            ("How to watch France vs Turkey: TV channel and live stream for Nations League today", "London Evening Standard"),
            ("Сборная Казахстана проиграла Молдове в Лиге наций", "Sports.kz"),
            ("Бумпром — Динамо-Минск-2 2:1: обзор матча, Первая лига, Тур 21", "Football.by"),
            ("Incredible comeback: Uzbekistan loses lead in match against Russia", "Sport"),
        ]
        for title, outlet in spam_cases:
            self.assertTrue(textutil.is_sports_stream_spam(title, outlet=outlet), f"Expected spam reject for: {title}")

        real_cases = [
            ("Estonia to close Russian border crossings over suspected sabotage", "Business Day"),
            ("Turkey and Qatar sign mutual defense pact", "Israel National News"),
            ("Australia signs defence pact with Philippines amid China tensions", "Inquirer"),
        ]
        for title, outlet in real_cases:
            self.assertFalse(textutil.is_sports_stream_spam(title, outlet=outlet), f"False positive on real news: {title}")

        # _home must drop both stream spam and Sport and entertainment stories from briefing lists
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            s_spam = _story("spam1", category="foreign_policy", score=50.0, outlets=12, last_24h=94)
            s_spam["headline"]["title"] = "!+!LIVE. France v Turkey Match LIVE Stream Tv Channel"
            s_spam["headline"]["source"] = "Universitat de Barcelona"
            s_sport = _story("sport1", category="society", score=20.0, outlets=8, last_24h=10, themes=["Sport and entertainment"])
            s_real = _story("real1", category="foreign_policy", score=15.0, outlets=5, last_24h=4)
            d7 = {"totals": {"foreign_policy": 2, "society": 1}, "stories": [s_spam, s_sport, s_real]}
            (data_dir / "turkey-7d.json").write_text(json.dumps(d7), encoding="utf8")
            (data_dir / "turkey-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")
            with patch.object(export, "SITE_DATA", data_dir):
                home = export._home("2026-11-16T00:00:00+00:00", [{"id": "turkey", "name": "Turkey", "region": "Mediterranean"}])
            self.assertEqual([s["id"] for s in home["most_reported"]], ["real1"])
            self.assertEqual([s["id"] for s in home["growing"]], ["real1"])
            self.assertEqual(home["desks"][0]["lead"]["title"], "Headline real1")

    def test_home_clusters_elections_per_country_without_flooding_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            spain_elec = [
                _story(f"es_e{i}", category="internal_politics", score=20.0 - i, outlets=8 - i, last_24h=5,
                       themes=["Elections and political campaigns"])
                for i in range(7)
            ]
            spain_elec[2]["headline"]["title"] = "Bombing and riot at campaign rally"
            spain_non_elec = _story("es_econ", category="economy", score=12.0, outlets=6, last_24h=4, themes=["Economy"])
            malaysia_elec = _story("my_e0", category="internal_politics", score=11.0, outlets=4, last_24h=3,
                                   themes=["Elections and political campaigns"])
            (data_dir / "spain-7d.json").write_text(
                json.dumps({"totals": {"internal_politics": 7, "economy": 1}, "stories": spain_elec + [spain_non_elec]}),
                encoding="utf8",
            )
            (data_dir / "spain-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")
            (data_dir / "malaysia-7d.json").write_text(
                json.dumps({"totals": {"internal_politics": 1}, "stories": [malaysia_elec]}),
                encoding="utf8",
            )
            (data_dir / "malaysia-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")

            with patch.object(export, "SITE_DATA", data_dir):
                home = export._home("2026-11-16T00:00:00+00:00", [
                    {"id": "spain", "name": "Spain", "region": "Western Europe"},
                    {"id": "malaysia", "name": "Malaysia", "region": "Southeast Asia"},
                ])

            # One clustered election card per country; extra Spanish election stories stay inside election_cluster
            self.assertEqual([s["id"] for s in home["elections"]], ["es_e0", "my_e0"])
            cluster = home["elections"][0]["election_cluster"]
            self.assertEqual(cluster["count"], 7)
            self.assertEqual([sub["id"] for sub in cluster["stories"]], ["es_e1", "es_e2", "es_e3", "es_e4", "es_e5"])
            self.assertNotIn("election_cluster", home["elections"][1])

            # Overflow Spanish election stories must not flood growing or most_reported, while non-election stories stay
            self.assertEqual([s["id"] for s in home["growing"]], ["es_e0", "es_econ", "my_e0"])
            self.assertEqual([s["id"] for s in home["most_reported"]], ["es_e0", "es_econ", "my_e0"])

            # Directory count and violence monitor still see all underlying stories
            spain_desk = next(d for d in home["desks"] if d["id"] == "spain")
            self.assertEqual(spain_desk["elections"], 7)
            self.assertEqual([s["id"] for s in home["violent_events"]], ["es_e2"])

    def test_cross_country_desk_size_and_spam_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            # Vietnam (30-source desk): 6 outlets pumping 98 articles (30 in 24h)
            vn_spam = _story("vn_spam", category="foreign_policy", score=12.0, outlets=6, last_24h=30)
            vn_spam["articles"] = 98
            vn_spam["by_scope"] = {"domestic": 6, "abroad_local": 0, "international": 0}
            # France (16-source desk): 10 outlets with 12 genuine articles (10 in 24h)
            fr_real = _story("fr_real", category="foreign_policy", score=12.0, outlets=10, last_24h=10)
            fr_real["articles"] = 12
            fr_real["by_scope"] = {"domestic": 10, "abroad_local": 0, "international": 0}

            (data_dir / "vietnam-7d.json").write_text(json.dumps({"totals": {"foreign_policy": 1}, "stories": [vn_spam]}), encoding="utf8")
            (data_dir / "vietnam-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")
            (data_dir / "france-7d.json").write_text(json.dumps({"totals": {"foreign_policy": 1}, "stories": [fr_real]}), encoding="utf8")
            (data_dir / "france-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")

            with patch.object(export, "SITE_DATA", data_dir):
                home = export._home("2026-11-17T00:00:00+00:00", [
                    {"id": "vietnam", "name": "Vietnam", "region": "Southeast Asia"},
                    {"id": "france", "name": "France", "region": "Western Europe"},
                ])

            # France must beat Vietnam in both fastest growing and most reported
            self.assertEqual(home["growing"][0]["id"], "fr_real")
            self.assertEqual(home["most_reported"][0]["id"], "fr_real")
            # Equal outlet counts favor the tighter desk (France 5/16 > Vietnam 5/30)
            self.assertGreater(
                export._norm_breadth({"country": "france", "independent_sources": 5, "by_scope": {"domestic": 5}}),
                export._norm_breadth({"country": "vietnam", "independent_sources": 5, "by_scope": {"domestic": 5}}),
            )


if __name__ == "__main__":
    unittest.main()
