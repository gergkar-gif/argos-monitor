"""Stage 1: for every country pack, fetch every active feed (and any GDELT query) and store new article URLs."""
import json
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser

from . import packs
from .fetch import get
from .textutil import clean, parse_date

WINDOW_DAYS = 7      # the longest window the site shows
MAX_PER_FEED = 100   # feeds like VietnamNet return ~1000 items; keep the newest
LANGS = {"English": "en", "Vietnamese": "vi", "Hungarian": "hu"}
OUTLET_SUFFIX = re.compile(r"\s+[-–—|]\s+[^-–—|]{2,60}$")   # " - Reuters" at the end of a headline


def title_key(title):
    """Lower-case letters and digits only: the same headline compares equal across outlets and punctuation styles."""
    return re.sub(r"[\W_]+", "", (title or "").lower())


def _known_titles(db, country):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
    return {title_key(r[0]) for r in db.execute("SELECT title FROM article WHERE country=? AND COALESCE(published_at, fetched_at) >= ?",
                                                (country, cutoff))}


def ingest_aggregator(db, pack, src, feed, parsed, known):
    """A news aggregator feed (Google News search). Each item names its outlet, which becomes its own source, so
    independent-outlet counts stay honest. Only the headline is available: the item links to a redirect, so the
    page is never fetched ('nofetch') and such stories get no quoted sentences. An item whose headline we already
    hold is skipped, so a story is not counted twice."""
    overrides = {}
    for scope, names in (pack.get("aggregator_outlets") or {}).items():
        overrides.update({n.lower(): scope for n in names})
    added = 0
    for e in parsed.entries[:MAX_PER_FEED]:
        outlet = ((e.get("source") or {}).get("title") or "").strip(" |-–—")
        title = clean(e.get("title"))
        if outlet and title.endswith(outlet) and OUTLET_SUFFIX.search(title):
            title = clean(OUTLET_SUFFIX.sub("", title))
        url = e.get("link")
        if not (outlet and title and url) or title_key(title) in known:
            continue
        sid = "gn:" + re.sub(r"[^a-z0-9]+", "-", outlet.lower()).strip("-")
        scope = overrides.get(outlet.lower(), src["scope"])
        db.execute("INSERT OR IGNORE INTO source VALUES (?,?,?,?,?,'media','found via Google News',0,0,'aggregator item')",
                   (sid, outlet, ((e.get("source") or {}).get("href") or ""), src["language"], scope))
        cur = db.execute(
            "INSERT OR IGNORE INTO article (source_id,feed_id,url,title,lead,language,published_at,fetched_at,extract_status,country) "
            "VALUES (?,?,?,?,'',?,?,?,'nofetch',?)",
            (sid, feed["id"], url, title, src["language"], parse_date(e), now(), pack["id"]))
        if cur.rowcount:
            known.add(title_key(title))
            added += 1
    return added


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_registry(db):
    """Write every pack's outlets and feeds into the database. A feed address may belong to one pack only."""
    seen, owners = {}, {}
    for country in packs.pack_ids():
        for s in packs.load(country)["sources"]:
            if owners.setdefault(s["id"], country) != country:
                raise SystemExit(f"Source id {s['id']} is used by two country packs ({owners[s['id']]} and {country}): ids must be unique.")
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
    by_id = {s["id"]: s for s in pack["sources"]}
    known = _known_titles(db, country)
    # Direct feeds first and aggregators last, so a headline we already hold directly is not added a second time.
    feeds = sorted(feeds, key=lambda f: bool(by_id[f["source_id"]].get("aggregator")))
    for feed in feeds:
        code, body = get(feed["url"])
        parsed = feedparser.parse(body) if code == 200 else None
        if not parsed or not parsed.entries:
            db.execute("UPDATE feed SET last_error=? WHERE id=?", (f"HTTP {code}, no items", feed["id"]))
            print(f"  FAIL {feed['url']} (HTTP {code})")
            continue
        if by_id[feed["source_id"]].get("aggregator"):
            n = ingest_aggregator(db, pack, by_id[feed["source_id"]], feed, parsed, known)
            db.execute("UPDATE feed SET last_ok_at=?, last_error=NULL WHERE id=?", (now(), feed["id"]))
            added += n
            print(f"  ok   {country[:4]} {feed['source_id']:15} {feed['section_label'] or '':22} +{n}")
            db.commit()
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
            if cur.rowcount:
                known.add(title_key(title))
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
