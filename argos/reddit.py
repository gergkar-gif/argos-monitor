"""Stage: what people talk about on the country's subreddits today (top posts of the day, via Reddit's public RSS).

Supports a list of subreddits per country in pack.yaml (e.g. [Vietnam, vozforums, TroChuyenLinhTinh, hanoi, Saigon])
and fetches all countries in one multireddit RSS request first to avoid Reddit's 1-request-per-minute IP rate limit.
"""
import re
import time
from datetime import datetime, timezone

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write

URL = "https://www.reddit.com/r/{}/top/.rss?t=day&limit=100"
POSTS = 6
SUB_RE = re.compile(r"/r/([^/]+)/")


def _subs(pack):
    r = pack.get("reddit") or []
    return [r] if isinstance(r, str) else list(r)


def _post(e):
    m = SUB_RE.search(e.get("link") or "")
    return {"title": e.title, "url": e.link, "sub": m.group(1) if m else ""}


def run(db=None):
    by_country = {cid: _subs(packs.load(cid)) for cid in packs.pack_ids()}
    owner = {s.lower(): cid for cid, subs in by_country.items() for s in subs}
    out = {}
    all_subs = "+".join(s for subs in by_country.values() for s in subs)
    status, body = fetch.get(URL.format(all_subs)) if all_subs else (0, b"")
    if status == 429:
        time.sleep(60)
        status, body = fetch.get(URL.format(all_subs))
    if status == 200:
        buckets = {cid: [] for cid in by_country}
        for e in feedparser.parse(body).entries:
            p = _post(e)
            cid = owner.get(p["sub"].lower())
            if cid and len(buckets[cid]) < POSTS:
                buckets[cid].append(p)
        for cid, subs in by_country.items():
            if buckets[cid]:
                out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in subs), "posts": buckets[cid]}
                print(f"reddit: {cid}: {len(buckets[cid])} posts across {out[cid]['subreddit']}")
    # Top up any country that had no posts in the global top-100 (e.g. smaller subreddits like Cambodia).
    for cid, subs in by_country.items():
        if cid in out or not subs:
            continue
        status, body = fetch.get(URL.format("+".join(subs)))
        if status == 429:
            time.sleep(60)
            status, body = fetch.get(URL.format("+".join(subs)))
        if status != 200:
            print(f"reddit: {cid}: HTTP {status}, skipped")
            continue
        posts = [_post(e) for e in feedparser.parse(body).entries[:POSTS]]
        if posts:
            out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in subs), "posts": posts}
            print(f"reddit: {cid}: {len(posts)} posts across {out[cid]['subreddit']}")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("reddit", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_REDDIT")
