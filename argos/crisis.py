"""Stage: crisis and official alerts per country, from free official feeds (GDACS, USGS, UK and US travel advice).
Only each feed's own title, link and date are kept: no sentences of our own. A feed that fails is skipped."""
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write

GDACS = "https://www.gdacs.org/xml/rss.xml"
USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.atom"
US = "https://travel.state.gov/_res/rss/TAsTWs.xml"
UK = "https://www.gov.uk/foreign-travel-advice/{}.atom"
RECENT_DAYS = 7


def _feed(url):
    status, body = fetch.get(url)
    if status != 200:
        print(f"crisis: {url} -> HTTP {status}, skipped")
        return []
    return feedparser.parse(body).entries


def _when(e):
    raw = e.get("published") or e.get("updated")
    try:
        d = parsedate_to_datetime(raw) if "," in raw else datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _item(kind, e, level=None):
    d = _when(e)
    return {"kind": kind, "title": re.sub(r"\s+", " ", e.title).strip(), "url": e.link, "level": level,
            "date": d.isoformat(timespec="seconds") if d else None}


def run(db=None):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=RECENT_DAYS)
    gdacs, usgs, us = _feed(GDACS), _feed(USGS), _feed(US)
    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", [])]]
        has = lambda text: any(re.search(rf"\b{re.escape(n)}\b", (text or "").lower()) for n in names)
        items = []
        items += [_item("GDACS", e, e.get("gdacs_alertlevel")) for e in gdacs if has(e.get("gdacs_country")) or has(e.title)]
        items += [_item("USGS", e) for e in usgs if has(e.title)]
        items += [_item("US travel advisory", e) for e in us if has(e.title.split(" - ")[0])]
        items += [_item("UK travel advice", e) for e in _feed(UK.format(pack["name"].lower().replace(" ", "-")))[:1]]
        # disasters older than a week are history; travel advice stays until the government changes it
        items = [i for i in items if "travel" in i["kind"] or (i["date"] and datetime.fromisoformat(i["date"]) >= recent)]
        out[cid] = sorted(items, key=lambda i: i["date"] or "", reverse=True)
        print(f"crisis: {cid}: {len(items)} items")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("crisis", {"generated_at": now.isoformat(timespec="seconds"), "countries": out}, "ARGOS_CRISIS")
