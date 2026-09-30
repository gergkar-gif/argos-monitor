"""Stage 1: read sources.yaml, fetch every active feed and GDELT query, store new article URLs."""
import json
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import yaml

from .config import SOURCES_YAML
from .fetch import get
from .textutil import clean, parse_date

VIETNAM = re.compile(r"vi[eê]t\s?nam|hanoi|ha noi|hà nội|ho chi minh|saigon|sài gòn", re.I)
WINDOW_DAYS = 7      # the MVP window
MAX_PER_FEED = 100   # feeds like VietnamNet return ~1000 items; keep the newest
LANGS = {"English": "en", "Vietnamese": "vi"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_registry(db):
    sources = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf8"))["sources"]
    for s in sources:
        db.execute("INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (s["id"], s["name"], s["homepage"], s["language"], s["scope"], s["kind"],
                    s["governing_body"], int(s["state_affiliated"]), int(s["reprints_vna"]), s.get("notes")))
        for f in s.get("feeds", []):
            db.execute("INSERT INTO feed (source_id,url,section_label,category_hint,active) VALUES (?,?,?,?,?) "
                       "ON CONFLICT(url) DO UPDATE SET source_id=excluded.source_id, section_label=excluded.section_label, "
                       "category_hint=excluded.category_hint, active=excluded.active",
                       (s["id"], f["url"], f.get("section"), f.get("category_hint"), int(f.get("active", True))))
    urls = [f["url"] for s in sources for f in s.get("feeds", [])]
    db.execute(f"UPDATE feed SET active=0 WHERE url NOT IN ({','.join('?' * len(urls))})", urls)  # feeds removed from the yaml
    db.commit()
    return sources


def ingest_feeds(db, sources):
    # International feeds cover many topics, so keep only items that mention Vietnam.
    filtered = {s["id"] for s in sources if s["scope"] == "international"}
    added = 0
    feeds = db.execute("SELECT f.*, s.language FROM feed f JOIN source s ON s.id=f.source_id WHERE f.active=1").fetchall()
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
            if feed["source_id"] in filtered and not VIETNAM.search(title + " " + lead):
                continue
            cur = db.execute(
                "INSERT OR IGNORE INTO article (source_id,feed_id,url,title,lead,language,published_at,fetched_at,extract_status) "
                "VALUES (?,?,?,?,?,?,?,?,'pending')",
                (feed["source_id"], feed["id"], url, title, lead, feed["language"], parse_date(e), now()))
            n += cur.rowcount
        db.execute("UPDATE feed SET last_ok_at=?, last_error=NULL WHERE id=?", (now(), feed["id"]))
        added += n
        print(f"  ok   {feed['source_id']:15} {feed['section_label'] or '':22} +{n}")
        db.commit()
    return added


def ingest_gdelt(db, sources):
    added = 0
    for s in sources:
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
                    "INSERT OR IGNORE INTO article (source_id,url,title,lead,language,published_at,fetched_at,extract_status) "
                    "VALUES (?,?,?,'',?,?,?,'pending')",
                    (sid, a["url"], clean(a["title"]), lang, seen.isoformat(timespec="seconds"), now()))
                added += cur.rowcount
            db.commit()
            print(f"  ok   GDELT: {len(arts)} results")
    return added


def run(db):
    sources = load_registry(db)
    a = ingest_feeds(db, sources)
    b = ingest_gdelt(db, sources)
    print(f"ingest: {a} new from feeds, {b} new from GDELT")
