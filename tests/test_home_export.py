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


if __name__ == "__main__":
    unittest.main()
