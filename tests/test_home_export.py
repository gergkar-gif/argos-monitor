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

            with patch.object(export, "SITE_DATA", data_dir), patch.object(export, "_desk_outlet_scale", return_value=20):
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
            # Malaysia (15-source desk): 10 outlets with 12 genuine articles (10 in 24h)
            my_real = _story("my_real", category="foreign_policy", score=12.0, outlets=10, last_24h=10)
            my_real["articles"] = 12
            my_real["by_scope"] = {"domestic": 10, "abroad_local": 0, "international": 0}

            (data_dir / "vietnam-7d.json").write_text(json.dumps({"totals": {"foreign_policy": 1}, "stories": [vn_spam]}), encoding="utf8")
            (data_dir / "vietnam-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")
            (data_dir / "malaysia-7d.json").write_text(json.dumps({"totals": {"foreign_policy": 1}, "stories": [my_real]}), encoding="utf8")
            (data_dir / "malaysia-24h.json").write_text(json.dumps({"totals": {}, "stories": []}), encoding="utf8")

            with patch.object(export, "SITE_DATA", data_dir):
                home = export._home("2026-11-17T00:00:00+00:00", [
                    {"id": "vietnam", "name": "Vietnam", "region": "Southeast Asia"},
                    {"id": "malaysia", "name": "Malaysia", "region": "Southeast Asia"},
                ])

            # Smaller desk with genuine multi-outlet breadth must beat Vietnam in both fastest growing and most reported
            self.assertEqual(home["growing"][0]["id"], "my_real")
            self.assertEqual(home["most_reported"][0]["id"], "my_real")
            # Equal outlet counts favor the tighter desk (Malaysia 5/15 > Vietnam 5/30)
            self.assertGreater(
                export._norm_breadth({"country": "malaysia", "independent_sources": 5, "by_scope": {"domestic": 5}}),
                export._norm_breadth({"country": "vietnam", "independent_sources": 5, "by_scope": {"domestic": 5}}),
            )

    def test_russia_ukraine_morphology_scope_ratings_and_themes(self):
        from argos import ratings
        packs.load.cache_clear()
        ru = packs.load("russia")
        ua = packs.load("ukraine")

        # Inflected Russian & Ukrainian cases must pass abroad_local / foreign-section relevance gates
        self.assertTrue(relevance.is_relevant(
            ru, "abroad_local", "general", "", "https://thebell.io/story",
            "Эстония с 1 декабря закроет границу с Россией", "", "",
        ))
        self.assertTrue(relevance.is_relevant(
            ru, "abroad_local", "general", "", "https://istories.media/news/1",
            "В Москве задержали подозреваемую в подрыве", "", "",
        ))
        self.assertFalse(relevance.is_relevant(
            ru, "abroad_local", "general", "", "https://istories.media/news/2",
            "Даниил Медведев вышел в полуфинал турнира в ОАЭ", "", "",
        ))
        self.assertFalse(relevance.is_relevant(
            ru, "domestic", "general", "", "https://tass.ru/mezhdunarodnaya-panorama/123",
            "В Гагаузии проходит голосование на выборах главы автономии", "", "",
        ))

        self.assertTrue(relevance.is_relevant(
            ua, "abroad_local", "general", "", "https://www.radiosvoboda.org/a/1",
            "Сибіга анонсував зустріч Зеленського і Петера Мадяра", "", "",
        ))
        self.assertTrue(relevance.is_relevant(
            ua, "abroad_local", "general", "", "https://www.radiosvoboda.org/a/2",
            "У Києві уламки БпЛА впали у дворі багатоповерхівки", "", "",
        ))
        self.assertFalse(relevance.is_relevant(
            ua, "domestic", "general", "", "https://www.ukrinform.ua/rubric-world/123",
            "Президент Монголії оголосив про відставку", "", "",
        ))
        self.assertFalse(relevance.is_relevant(
            ua, "domestic", "general", "", "https://glavred.net/life/123",
            "Дорогі ароматизатори більше не потрібні", "", "",
        ))

        # Cyrillic Google News outlets must resolve accurately to domestic / abroad_local and non-unrated ratings
        self.assertEqual(packs.resolve_scope("ukraine", "gn:українська-правда", "Українська правда", "international", "international"), "domestic")
        self.assertEqual(packs.resolve_scope("ukraine", "gn:суспільне-новини", "Суспільне | Новини", "international", "international"), "domestic")
        self.assertEqual(packs.resolve_scope("ukraine", "gn:радіо-свобода", "Радіо Свобода", "international", "international"), "abroad_local")
        self.assertEqual(packs.resolve_scope("russia", "gn:медиазона", "Медиазона", "international", "international"), "abroad_local")
        self.assertEqual(packs.resolve_scope("russia", "gn:российская-газета", "Российская газета", "international", "international"), "domestic")

        self.assertEqual(ratings.lookup_rating("ОВД-Инфо")["factuality"], "very_high")
        self.assertEqual(ratings.lookup_rating("OVD-Info")["factuality"], "very_high")
        self.assertEqual(ratings.lookup_rating("Bihus.Info")["factuality"], "very_high")
        self.assertEqual(ratings.lookup_rating("Суспільне | Новини")["alignment"], "public_broadcaster")
        self.assertEqual(ratings.lookup_rating("Президент России")["alignment"], "state_controlled")

        # Inflected Russian & Ukrainian war/sanctions/sports headlines must trigger exact theme keywords
        ru_def = next(t for t in ru["themes"]["themes"] if t["id"] == "wartime_defense_mobilization")
        ru_sport = next(t for t in ru["themes"]["themes"] if t["id"] == "sport_culture")
        self.assertGreater(policy._keyword_share([("собянин: силы пво сбили три летевших на москву бпла", "")], ru_def["keywords"]), 0.0)
        self.assertGreater(policy._keyword_share([("кагановская и некрасов победили в танцах на льду на этапе гран-при в омске", "")], ru_sport["keywords"]), 0.0)

        ua_def = next(t for t in ua["themes"]["themes"] if t["id"] == "defence_security")
        self.assertGreater(policy._keyword_share([("у запоріжжі через удар російського дрона поранена жінка", "")], ua_def["keywords"]), 0.0)
        self.assertGreater(policy._keyword_share([("польща призупинила фінансування закупівель американської зброї", "")], ua_def["keywords"]), 0.0)
        self.assertTrue(textutil.is_sports_stream_spam("Журова о допуске к МЧМ", outlet="Sportbox"))

    def test_china_traditional_simplified_scope_ratings_themes_and_excerpts(self):
        from argos import excerpts, ratings
        packs.load.cache_clear()
        cn = packs.load("china")

        # Both Traditional Chinese (BBC Chinese / Initium) and Simplified Chinese must pass abroad_local gates
        self.assertTrue(relevance.is_relevant(
            cn, "abroad_local", "general", "", "https://www.bbc.com/zhongwen/articles/1",
            "APEC深圳峰會：中方確認美中俄會晤，習近平將主持會議", "", "",
        ))
        self.assertTrue(relevance.is_relevant(
            cn, "abroad_local", "general", "", "https://theinitium.com/20261117-mainland",
            "中國如何成為「水電國家」？專訪環境史學者", "", "",
        ))
        # Pure Taipei local election or foreign non-China story must be rejected on abroad_local
        self.assertFalse(relevance.is_relevant(
            cn, "abroad_local", "general", "", "https://theinitium.com/20261117-whatsnew",
            "台北市長封關民調出爐：四家結果兩勝兩負", "", "",
        ))
        self.assertFalse(relevance.is_relevant(
            cn, "domestic", "general", "", "https://www.scmp.com/news/world/europe/123",
            "French lawmakers debate pension budget", "", "",
        ))

        # English & Chinese Google News outlets on China desk must resolve accurately
        self.assertEqual(packs.resolve_scope("china", "gn:reuters", "Reuters", "international", "international"), "international")
        self.assertEqual(packs.resolve_scope("china", "gn:人民网", "人民网", "domestic", "domestic"), "domestic")
        self.assertEqual(packs.resolve_scope("china", "gn:bbc-news-中文", "BBC News 中文", "domestic", "domestic"), "abroad_local")
        self.assertEqual(packs.resolve_scope("china", "gn:纽约时报中文网", "纽约时报中文网", "domestic", "domestic"), "abroad_local")

        # PRC state outlets and HK/overseas outlets must not resolve as unrated/independent
        self.assertEqual(ratings.lookup_rating("人民网")["alignment"], "state_controlled")
        self.assertEqual(ratings.lookup_rating("央视网")["alignment"], "state_controlled")
        self.assertEqual(ratings.lookup_rating("军网")["alignment"], "state_controlled")
        self.assertEqual(ratings.lookup_rating("ThePaper.cn")["alignment"], "state_controlled")
        self.assertEqual(ratings.lookup_rating("北京市人民政府门户网站")["alignment"], "state_controlled")
        self.assertEqual(ratings.lookup_rating("Hong Kong Free Press")["alignment"], "independent")
        self.assertEqual(ratings.lookup_rating("The Witness (法庭線)")["factuality"], "very_high")

        # Latin acronyms embedded inside CJK text (e.g. 读懂APEC / 中国GDP) must match theme keywords
        dip = next(t for t in cn["themes"]["themes"] if t["id"] == "diplomacy")
        sport = next(t for t in cn["themes"]["themes"] if t["id"] == "sport_culture")
        weather = next(t for t in cn["themes"]["themes"] if t["id"] == "accident_weather")
        self.assertGreater(policy._keyword_share([("一组数据读懂apec“中国年”新机遇", "")], dip["keywords"]), 0.0)
        self.assertGreater(policy._keyword_share([("中国队，拿下13金！", "")], sport["keywords"]), 0.0)
        self.assertGreater(policy._keyword_share([("冷空气到场！北京周末再迎弱雨雪", "")], weather["keywords"]), 0.0)

        # CJK full-text sentences ending in Chinese punctuation must be extracted verbatim
        sample_txt = "原标题\n中国国务院副总理表示，必须加快人工智能与半导体领域自主创新能力建设。\n国际机构指出，该政策旨在强化本土供应链韧性。"
        spans = excerpts.sentences(sample_txt, cn)
        self.assertEqual(len(spans), 2)
        for s, e in spans:
            self.assertEqual(sample_txt[s:e], sample_txt[s:e])
            self.assertTrue(sample_txt[s:e].endswith("。"))

    def test_east_asia_sibling_desks_scopes_themes_and_ratings(self):
        from argos import packs, policy, ratings, relevance, textutil

        # Taiwan: avoid generic semiconductor leak; resolve domestic vs abroad_local; check Traditional Chinese keywords
        tw = packs.load("taiwan")
        self.assertFalse(relevance.is_relevant(tw, "international", "general", "", "https://example.com/1", "全球半導體關稅衝擊歐洲車廠", "", ""))
        self.assertTrue(relevance.is_relevant(tw, "international", "general", "", "https://example.com/2", "台積電擴大美國亞利桑那廠投資", "", ""))
        self.assertEqual(packs.resolve_scope("taiwan", "gn:udn", "UDN", "domestic", "domestic"), "domestic")
        self.assertEqual(packs.resolve_scope("taiwan", "gn:bbc-news-中文", "BBC News 中文", "domestic", "domestic"), "abroad_local")
        self.assertEqual(ratings.lookup_rating("Focus Taiwan")["alignment"], "public_broadcaster")
        self.assertEqual(ratings.lookup_rating("PTS News (公視新聞網)")["alignment"], "public_broadcaster")
        self.assertEqual(ratings.lookup_rating("工商時報")["bias"], "center-right")
        tw_el = next(t for t in tw["themes"]["themes"] if t["id"] == "elections")
        self.assertGreater(policy._keyword_share([("九合一地方選舉投票率創新高", "")], tw_el["keywords"]), 0.0)

        # Japan: current PM Takaichi mention match, scopes, ratings, Japanese elections
        jp = packs.load("japan")
        self.assertTrue(relevance.is_relevant(jp, "international", "general", "", "https://example.com/3", "2日の高市首相の動静", "", ""))
        self.assertEqual(packs.resolve_scope("japan", "gn:日本経済新聞", "日本経済新聞", "domestic", "domestic"), "domestic")
        self.assertEqual(packs.resolve_scope("japan", "gn:ニューズウィーク日本版", "ニューズウィーク日本版", "domestic", "domestic"), "abroad_local")
        self.assertEqual(ratings.lookup_rating("NHK News Web")["alignment"], "public_broadcaster")
        self.assertEqual(ratings.lookup_rating("Bunshun Online (文春オンライン)")["alignment"], "independent")
        self.assertEqual(ratings.lookup_rating("産経ニュース")["bias"], "right")

        # South Korea: bare 'won' must not match English verb; SBS must be independent; fnnews comma-date must parse
        kr = packs.load("south_korea")
        self.assertFalse(relevance.is_relevant(kr, "international", "general", "", "https://example.com/4", "Arsenal won the Premier League clash in London", "", ""))
        self.assertTrue(relevance.is_relevant(kr, "international", "general", "", "https://example.com/5", "이재명 대통령이 역대 최대 예산안을 발표했다", "", ""))
        self.assertEqual(packs.resolve_scope("south_korea", "gn:한국경제", "한국경제", "domestic", "domestic"), "domestic")
        self.assertEqual(packs.resolve_scope("south_korea", "gn:bbc-news-코리아", "BBC News 코리아", "domestic", "domestic"), "abroad_local")
        self.assertEqual(ratings.lookup_rating("SBS 뉴스 (SBS News)")["alignment"], "independent")
        self.assertEqual(textutil.parse_date({"published": "Thu,19 Nov 2026 01:07:10 +0900"}), "2026-11-18T16:07:10+00:00")

        # North Korea: bare '조선' must not match Chosun Ilbo; SK/US outlets must not resolve domestic; Sino-NK rated
        kp = packs.load("north_korea")
        self.assertFalse(relevance.is_relevant(kp, "abroad_local", "general", "", "https://example.com/6", "[조선일보] 서울 부동산 시장 전망", "", ""))
        self.assertTrue(relevance.is_relevant(kp, "abroad_local", "general", "", "https://example.com/7", "IAEA '영변 우라늄 농축시설 증축 완공'", "", ""))
        self.assertEqual(packs.resolve_scope("north_korea", "gn:reuters", "Reuters", "international", "international"), "international")
        self.assertEqual(packs.resolve_scope("north_korea", "gn:연합뉴스", "연합뉴스", "domestic", "abroad_local"), "abroad_local")
        self.assertEqual(packs.resolve_scope("north_korea", "gn:조선중앙통신", "조선중앙통신", "international", "international"), "domestic")
        self.assertEqual(ratings.lookup_rating("Sino-NK")["factuality"], "very_high")
        kp_ru = next(t for t in kp["themes"]["themes"] if t["id"] == "russia_dprk_military_alliance")
        self.assertGreater(policy._keyword_share([("북한군 러시아 쿠르스크 파병 확대", "")], kp_ru["keywords"]), 0.0)


if __name__ == "__main__":
    unittest.main()
