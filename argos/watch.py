"""Stage: write site/watch.xml, an RSS feed of the exported stories that mention a word from watchlist.yaml.
Only headlines and links, as on the site. Subscribe to <site address>/watch.xml in any feed reader."""
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

import yaml

from . import packs
from .config import ROOT
from .export import SITE_DATA


def run(db=None):
    raw_words = [str(w).strip() for w in (yaml.safe_load((ROOT / "watchlist.yaml").read_text(encoding="utf8")) or {}).get("watch", []) if str(w).strip()]
    matchers = [(w, re.compile(packs._term_regex(w), re.I)) for w in raw_words]
    items = []
    for f in sorted(SITE_DATA.glob("*-7d.json")):
        d = json.loads(f.read_text(encoding="utf8"))
        for s in d["stories"]:
            h_obj = s.get("headline") or {}
            text = " ".join([
                h_obj.get("title") or "",
                h_obj.get("en_title") or "",
                *(r.get("title") or "" for r in s.get("sources", [])),
                *(x.get("text") or "" for x in s.get("excerpts", [])),
            ])
            hit = [w for w, rx in matchers if rx.search(text)]
            if hit:
                items.append((s["last_seen"], d["country"], hit, s))
    items.sort(key=lambda i: i[0], reverse=True)
    body = "".join(
        f"<item><title>{escape(s['headline'].get('en_title') or s['headline']['title'])}</title><link>{escape(s['headline']['url'])}</link>"
        f"<guid>{escape(s['headline']['url'])}</guid><category>{escape(c)}</category>"
        f"<description>{escape(', '.join(hit))}: {s['articles']} articles, {s['independent_sources']} independent outlets</description>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(seen))}</pubDate></item>" for seen, c, hit, s in items[:100])
    (SITE_DATA.parent / "watch.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>Argos Monitor watchlist</title>'
        f"<link>https://argosmonitor.uk/</link><description>Argos Monitor watchlist feed</description>{body}</channel></rss>",
        encoding="utf8")
    print(f"watch: {len(items)} stories match {len(raw_words)} words")
