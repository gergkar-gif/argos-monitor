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
CRISISGROUP = "https://www.crisisgroup.org/rss"
UN_PEACE = "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml"
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
    if not raw:
        return None
    try:
        if " - " in raw:
            try:
                d = datetime.strptime(raw, "%A, %B %d, %Y - %H:%M")
            except ValueError:
                d = parsedate_to_datetime(raw)
        elif "," in raw:
            d = parsedate_to_datetime(raw)
        else:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
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
    gdacs, usgs, eonet, us, cg, un = _feed(GDACS), _feed(USGS), _eonet(), _feed(US), _feed(CRISISGROUP), _feed(UN_PEACE)
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
        # UN Peace & Security conflict, civilian protection, and armed incident updates (last 30 days).
        un_items = [_item("UN Peace & Security", e, "Security") for e in un if has(e.title) or has(e.get("summary"))]
        items += [i for i in un_items if i["date"] and datetime.fromisoformat(i["date"]) >= now - timedelta(days=30)]
        # Crisis Group updates within the last 30 days.
        cg_items = [_item("Crisis Group", e) for e in cg if has(e.title) or has(e.get("summary"))]
        items += [i for i in cg_items if i["date"] and datetime.fromisoformat(i["date"]) >= now - timedelta(days=30)]
        # Skip routine "Level 1: Exercise Normal Precautions" so the alerts list only shows elevated advisories (Level 2-4).
        for e in us:
            if has(e.title.split(" - ")[0]) and "Level 1" not in e.title:
                lvl = "Warning" if "Level 4" in e.title else ("Alert" if "Level 3" in e.title else "Caution")
                items.append(_item("US travel advisory", e, lvl))
        # Include UK travel advice updates within the last 30 days.
        uk_slug = pack.get("uk_slug") or pack["name"].lower().replace(" ", "-")
        uk = [_item("UK travel advice", e) for e in _feed(UK.format(uk_slug))[:3]]
        items += [i for i in uk if i["date"] and datetime.fromisoformat(i["date"]) >= now - timedelta(days=30)]
        # Disasters older than a week are history; active elevated travel advisories, UN peace/security, and conflict reports stay up to 30 days.
        items = [i for i in items if "travel" in i["kind"] or "Crisis Group" in i["kind"] or "UN Peace" in i["kind"] or (i["date"] and datetime.fromisoformat(i["date"]) >= recent)]
        out[cid] = sorted(items, key=lambda i: i["date"] or "", reverse=True)
        print(f"crisis: {cid}: {len(items)} items")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("crisis", {"generated_at": now.isoformat(timespec="seconds"), "countries": out}, "ARGOS_CRISIS")
