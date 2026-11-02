"""Stage: what people search for right now, from Google Trends' public RSS feed, one list per country.
Only the search term, its rough traffic and Google's own news link are kept. A failed feed is skipped."""
from datetime import datetime, timezone

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write

URL = "https://trends.google.com/trending/rss?geo={}"


def run(db=None):
    out = {}
    for cid in packs.pack_ids():
        geo = packs.load(cid).get("geo")
        status, body = fetch.get(URL.format(geo)) if geo else (0, b"")
        if status != 200:
            print(f"trends: {cid}: HTTP {status}, skipped")
            continue
        out[cid] = [{"term": e.title, "traffic": e.get("ht_approx_traffic"), "news": e.get("ht_news_item_title"),
                     "url": e.get("ht_news_item_url"), "source": e.get("ht_news_item_source")}
                    for e in feedparser.parse(body).entries]
        print(f"trends: {cid}: {len(out[cid])} searches")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("trends", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_TRENDS")
