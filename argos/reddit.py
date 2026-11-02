"""Stage: what people talk about on the country's main subreddit today (top posts of the day, via Reddit's public RSS).
Optional: Reddit sometimes refuses cloud servers, in which case this country is skipped and the panel stays hidden."""
import time
from datetime import datetime, timezone

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write

URL = "https://www.reddit.com/r/{}/top/.rss?t=day"
POSTS = 5


def run(db=None):
    out = {}
    for cid in packs.pack_ids():
        sub = packs.load(cid).get("reddit")
        status, body = fetch.get(URL.format(sub)) if sub else (0, b"")
        if status == 429:     # Reddit asks for patience: wait once and try again
            time.sleep(10)
            status, body = fetch.get(URL.format(sub))
        time.sleep(3)
        if status != 200:
            print(f"reddit: {cid}: HTTP {status}, skipped")
            continue
        out[cid] = {"subreddit": sub, "posts": [{"title": e.title, "url": e.link} for e in feedparser.parse(body).entries[:POSTS]]}
        print(f"reddit: {cid}: {len(out[cid]['posts'])} posts")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("reddit", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_REDDIT")
