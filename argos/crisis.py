"""Stage: crisis and official alerts per country, from free official feeds (GDACS, USGS, UK and US travel advice).
Only each feed's own title, verbatim summary, link and date are kept: no sentences of our own."""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write

GDACS = "https://www.gdacs.org/xml/rss.xml"
USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.atom"
EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=14&limit=80"
US = "https://travel.state.gov/_res/rss/TAsTWs.xml"
UK = "https://www.gov.uk/foreign-travel-advice/{}.atom"
RECENT_DAYS = 7


def _eonet():
    status, body = fetch.get(EONET)
    if status != 200:
        return []
    try:
        return json.loads(body.decode("utf-8", errors="replace")).get("events") or []
    except ValueError:
        return []


def _feed(url):
    status, body = fetch.get(url)
    if status != 200:
        print(f"crisis: {url} -> HTTP {status}, skipped")
        return []
    return feedparser.parse(body.decode("utf-8", errors="replace")).entries


def _when(e):
    raw = e.get("published") or e.get("updated")
    try:
        d = parsedate_to_datetime(raw) if "," in raw else datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _summary(kind, e):
    raw = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary") or ""))
    raw = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s+", " ", raw)).strip()
    if kind == "US travel advisory":
        for s in re.split(r"(?<=\.)\s+", raw):
            if "due to" in s.lower() or "precaution" in s.lower():
                return s
    return raw.split(". ")[0] + ("." if raw and not raw.split(". ")[0].endswith(".") else "") if raw else ""


def _item(kind, e, level=None):
    d = _when(e)
    title = re.sub(r"\s+", " ", e.title).strip()
    summary = _summary(kind, e)
    # UK atom feeds set every title to "<Country> travel advice" and put the actual change note in <summary>.
    if kind == "UK travel advice" and summary:
        title, summary = summary, ""
    return {"kind": kind, "title": title, "summary": summary, "url": e.link, "level": level,
            "date": d.isoformat(timespec="seconds") if d else None}


def run(db=None):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=RECENT_DAYS)
    gdacs, usgs, eonet, us = _feed(GDACS), _feed(USGS), _eonet(), _feed(US)
    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", [])]]
        has = lambda text: any(re.search(rf"\b{re.escape(n)}\b", (text or "").lower()) for n in names)
        items = []
        items += [_item("GDACS", e, e.get("gdacs_alertlevel")) for e in gdacs if has(e.get("gdacs_country")) or has(e.title)]
        items += [_item("USGS", e) for e in usgs if has(e.title)]
        for ev in eonet:
            if has(ev.get("title")):
                cat = ((ev.get("categories") or [{}])[0]).get("title") or "Natural event"
                src_url = ((ev.get("sources") or [{}])[0]).get("url") or ev.get("link") or ""
                dt = ((ev.get("geometry") or [{}])[-1]).get("date")
                items.append({"kind": "NASA EONET", "title": ev["title"], "summary": cat, "url": src_url, "level": None, "date": dt})
        # Skip routine "Level 1: Exercise Normal Precautions" so the alerts list only shows elevated advisories (Level 2-4).
        items += [_item("US travel advisory", e) for e in us if has(e.title.split(" - ")[0]) and "Level 1" not in e.title]
        # Only include UK travel advice if it was updated within the last 30 days.
        uk = [_item("UK travel advice", e) for e in _feed(UK.format(pack["name"].lower().replace(" ", "-")))[:1]]
        items += [i for i in uk if i["date"] and datetime.fromisoformat(i["date"]) >= now - timedelta(days=30)]
        # Disasters older than a week are history; active elevated travel advisories stay.
        items = [i for i in items if "travel" in i["kind"] or (i["date"] and datetime.fromisoformat(i["date"]) >= recent)]
        out[cid] = sorted(items, key=lambda i: i["date"] or "", reverse=True)
        print(f"crisis: {cid}: {len(items)} items")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("crisis", {"generated_at": now.isoformat(timespec="seconds"), "countries": out}, "ARGOS_CRISIS")
