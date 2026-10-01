"""Stage 1: for every country pack, fetch every active feed (and any GDELT query) and store new article URLs."""
import json
import time
from datetime import datetime, timedelta, timezone

import feedparser

from . import packs
from .fetch import get
from .textutil import clean, parse_date

WINDOW_DAYS = 7      # the longest window the site shows
MAX_PER_FEED = 100   # feeds like VietnamNet return ~1000 items; keep the newest
LANGS = {"English": "en", "Vietnamese": "vi", "Hungarian": "hu"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_registry(db):
    """Write every pack's outlets and feeds into the database. A feed address may belong to one pack only."""
    seen = {}
    for country in packs.pack_ids():
        for s in packs.load(country)["sources"]:
            db.execute("INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (s["id"], s["name"], s["homepage"], s["language"], s["scope"], s["kind"],
                        s["governing_body"], int(s["state_affiliated"]), int(s.get("reprints_vna", False)), s.get("notes")))
            for f in s.get("feeds", []):
                if seen.setdefault(f["url"], country) != country:
                    raise SystemExit(f"Feed {f['url']} is listed in two country packs ({seen[f['url']]} and {country}).")
                db.execute("INSERT INTO feed (source_id,url,section_label,category_hint,active) VALUES (?,?,?,?,?) "
                           "ON CONFLICT(url) DO UPDATE SET source_id=excluded.source_id, section_label=excluded.section_label, "
                           "category_hint=excluded.category_hint, active=excluded.active",
                           (s["id"], f["url"], f.get("section"), f.get("category_hint"), int(f.get("active", True))))
    urls = list(seen)
    db.execute(f"UPDATE feed SET active=0 WHERE url NOT IN ({','.join('?' * len(urls))})", urls)   # feeds removed from a yaml
    db.commit()


def ingest_feeds(db, country):
    pack = packs.load(country)
    # International feeds cover many topics, so keep only items that mention the country.
    international = {s["id"] for s in pack["sources"] if s["scope"] == "international"}
    ids = [s["id"] for s in pack["sources"]]
    feeds = db.execute(f"SELECT f.*, s.language FROM feed f JOIN source s ON s.id=f.source_id WHERE f.active=1 "
                       f"AND f.source_id IN ({','.join('?' * len(ids))})", ids).fetchall()
    added = 0
    for feed in feeds:
        code, body = get(feed["url"])
        parsed = feedparser.parse(body) if code == 200 else None
        if not parsed or not parsed.entries:
            db.execute("UPDATE feed SET last_error=? WHERE id=?", (f"HTTP {code}, no items", feed["id"]))
            print(f"  FAIL {feed['url']} (HTTP {code})")
            continue
        n = 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat(timespec="seconds")
        entries = sorted(parsed.entries, key=lambda e: parse_date(e) or "", reverse=True)[:MAX_PER_FEED]
        for e in entries:
            if (parse_date(e) or cutoff) < cutoff:
                continue
            url, title = e.get("link"), clean(e.get("title"))
            lead = clean(e.get("summary") or e.get("description"))
            if not url or not title:
                continue
            if feed["source_id"] in international and not pack["mention_re"].search(title + " " + lead):
                continue
            cur = db.execute(
                "INSERT OR IGNORE INTO article (source_id,feed_id,url,title,lead,language,published_at,fetched_at,extract_status,country) "
                "VALUES (?,?,?,?,?,?,?,?,'pending',?)",
                (feed["source_id"], feed["id"], url, title, lead, feed["language"], parse_date(e), now(), country))
            n += cur.rowcount
        db.execute("UPDATE feed SET last_ok_at=?, last_error=NULL WHERE id=?", (now(), feed["id"]))
        added += n
        print(f"  ok   {country[:4]} {feed['source_id']:15} {feed['section_label'] or '':22} +{n}")
        db.commit()
    return added


def ingest_gdelt(db, country):
    """Optional discovery through the GDELT DOC API (a source with `api_queries`). GDELT has refused our requests
    since the start, so no pack uses it today."""
    added = 0
    for s in packs.load(country)["sources"]:
        for q in s.get("api_queries", []):
            for attempt in range(3):
                time.sleep(6 * (attempt + 1))  # GDELT allows one request per 5 seconds
                code, body = get(q, timeout=60)
                if code != 429:
                    break
            try:
                arts = json.loads(body).get("articles", [])
            except ValueError:
                print(f"  FAIL GDELT (HTTP {code})")
                continue
            for a in arts:
                domain = a["domain"].removeprefix("www.")
                sid = "gdelt:" + domain
                lang = LANGS.get(a.get("language"), (a.get("language") or "")[:2].lower())
                db.execute("INSERT OR IGNORE INTO source VALUES (?,?,?,?,'international','media','unknown',0,0,'found via GDELT')",
                           (sid, domain, "https://" + domain, lang))
                seen = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                cur = db.execute(
                    "INSERT OR IGNORE INTO article (source_id,url,title,lead,language,published_at,fetched_at,extract_status,country) "
                    "VALUES (?,?,?,'',?,?,?,'pending',?)",
                    (sid, a["url"], clean(a["title"]), lang, seen.isoformat(timespec="seconds"), now(), country))
                added += cur.rowcount
            db.commit()
    return added


def run(db):
    load_registry(db)
    for country in packs.pack_ids():
        print(f"ingest {country}")
        a = ingest_feeds(db, country)
        b = ingest_gdelt(db, country)
        print(f"ingest {country}: {a} new from feeds, {b} new from GDELT")
