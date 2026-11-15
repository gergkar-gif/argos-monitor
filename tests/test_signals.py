import unittest
from datetime import datetime, timedelta, timezone

from argos import reddit, social, trends


class TestSignals(unittest.TestCase):
    def test_trends_filters_sports_horoscope_and_bare_singletons(self):
        pack = {"skip_sections": {"sports"}}
        outlets = {"dân trí"}
        self.assertFalse(trends._keep(pack, outlets, {"term": "con giáp may mắn hôm nay", "news": "Tử vi ngày 14", "url": "https://ex.com/a", "source": "X"}))
        self.assertFalse(trends._keep(pack, outlets, {"term": "shai gilgeous-alexander", "news": "NBA stats", "url": "https://www.nba.com/player", "source": "NBA"}))
        self.assertFalse(trends._keep(pack, outlets, {"term": "cd tenerife", "news": "Portero suspendido", "url": "https://marca.com/futbol", "source": "Marca"}))
        self.assertFalse(trends._keep(pack, outlets, {"term": "hanoi", "news": None, "url": None, "source": None}))
        self.assertTrue(trends._keep(pack, outlets, {"term": "belgrád", "news": "Újabb hibákat találtak a Budapest–Belgrád vonalon", "url": "https://telex.hu/belfold/1", "source": "Telex"}))

    def test_social_recency_clip_and_dedupe(self):
        now = datetime(2026, 11, 14, 6, 0, tzinfo=timezone.utc)
        fresh = (now - timedelta(hours=3)).isoformat()
        stale = (now - timedelta(days=20)).isoformat()
        self.assertTrue(social._is_recent(fresh, now))
        self.assertFalse(social._is_recent(stale, now))

        clipped = social._clip("word " * 70, limit=50)
        self.assertTrue(clipped.endswith("…"))
        self.assertLessEqual(len(clipped), 52)

        deduped = social._dedupe_and_cap([
            {"platform": "bluesky", "author": "@kyivindependent.com", "url": "https://bsky.app/1", "published": fresh, "text": "US Democrats direct Musk to preserve records on Ukraine's Starlink"},
            {"platform": "telegram", "author": "@kyivindependent_official", "url": "https://t.me/1", "published": fresh, "text": "US Democrats direct Musk to preserve records on Ukraine's Starlink"},
        ])
        self.assertEqual(len(deduped), 1)

    def test_reddit_chunk_countries(self):
        by_country = {f"c{i}": [f"sub{i}a", f"sub{i}b"] for i in range(12)}
        batches = list(reddit._chunk_countries(list(by_country), by_country, max_countries=5, max_subs=15))
        self.assertEqual(len(batches), 3)
        self.assertEqual(sum(len(b) for b in batches), 12)


if __name__ == "__main__":
    unittest.main()
