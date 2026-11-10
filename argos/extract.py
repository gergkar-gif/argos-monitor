"""Stage 2: fetch each pending article page and extract the main text with trafilatura.
Polite: honours robots.txt and waits between requests to the same host."""
import os
import threading
import time
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import trafilatura

from .config import USER_AGENT
from .fetch import get
from .textutil import nfc

HOST_DELAY = 0.7  # seconds between requests to the same host
_locks, _last, _robots = {}, {}, {}
_guard = threading.Lock()


def _robots_for(origin):
    with _guard:
        if origin not in _robots:
            rp = urllib.robotparser.RobotFileParser()
            code, body = get(origin + "/robots.txt", timeout=15)
            rp.parse(body.decode("utf8", "ignore").splitlines() if code == 200 else [])  # none = allowed
            _robots[origin] = rp
        return _robots[origin]


def _wait_turn(host):
    with _guard:
        lock = _locks.setdefault(host, threading.Lock())
    with lock:
        gap = HOST_DELAY - (time.time() - _last.get(host, 0))
        if gap > 0:
            time.sleep(gap)
        _last[host] = time.time()


def _one(row):
    url = row["url"]
    u = urlparse(url)
    if not _robots_for(f"{u.scheme}://{u.netloc}").can_fetch(USER_AGENT, url):
        return row["id"], None, "robots"
    _wait_turn(u.netloc)
    code, body = get(url)
    if code != 200:
        return row["id"], None, f"http{code}"
    text = trafilatura.extract(body, include_comments=False, include_tables=False, favor_precision=True)
    if text and len(text) > 200:
        return row["id"], nfc(text), "ok"
    return row["id"], None, "empty"


def run(db, limit=None, workers=8, country=None):
    if limit is None and os.environ.get("ARGOS_EXTRACT_LIMIT"):
        limit = int(os.environ["ARGOS_EXTRACT_LIMIT"])
    country = country or os.environ.get("ARGOS_EXTRACT_COUNTRY")
    story_only = bool(os.environ.get("ARGOS_EXTRACT_STORY_ONLY"))

    where = ["extract_status='pending'"]
    params = []
    if country:
        where.append("country=?")
        params.append(country)
    if story_only:
        where.append("id IN (SELECT article_id FROM story_article)")

    where_clause = " AND ".join(where)
    sql = f"SELECT id,url FROM article WHERE {where_clause} ORDER BY (id IN (SELECT article_id FROM story_article)) DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = db.execute(sql, params).fetchall()
    print(f"extract: {len(rows)} pending articles")
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for aid, text, status in ex.map(_one, rows):
            db.execute("UPDATE article SET text=?, extract_status=? WHERE id=?", (text, status, aid))
            done += 1
            if done % 10 == 0 or done == len(rows):
                db.commit()
                print(f"  {done}/{len(rows)}")
    db.commit()
    for st, n in db.execute("SELECT extract_status, COUNT(*) FROM article GROUP BY 1"):
        print(f"  {st}: {n}")
