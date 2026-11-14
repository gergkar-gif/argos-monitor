"""Stage 2: fetch each pending article page and extract the main text with trafilatura.
Polite: honours robots.txt and waits between requests to the same host."""
import os
import threading
import time
import urllib.robotparser
from collections import defaultdict
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
            if code == 200:
                rp.parse(body.decode("utf8", "ignore").splitlines())
            elif code in (404, 410):
                rp.parse([])  # no robots.txt = allowed (RFC 9309)
            else:
                rp.parse(["User-agent: *", "Disallow: /"])  # transient error: fail closed
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


def _select_pending(db, limit=None, country=None, story_only=True):
    """Prioritize pending articles from top-ranked multi-outlet stories that lack extracted text,
    interleaved round-robin across country desks so alphabetical tail packs never starve earlier desks."""
    if not story_only:
        where = ["extract_status='pending'"]
        params = []
        if country:
            where.append("country=?")
            params.append(country)
        sql = f"SELECT id, url FROM article WHERE {' AND '.join(where)} ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return db.execute(sql, params).fetchall()

    cond = "WHERE COALESCE(sa.similarity, 1.0) >= 0.93" + (" AND s.country=?" if country else "")
    params = [country] if country else []
    rows = db.execute(
        f"SELECT s.id AS story_id, s.country, COALESCE(s.score, 0.0) AS score, s.representative_article_id, "
        f"a.id AS id, a.url AS url, a.extract_status, a.syndicated_of, (a.text IS NOT NULL) AS has_text "
        f"FROM story s JOIN story_article sa ON sa.story_id=s.id JOIN article a ON a.id=sa.article_id {cond}",
        params,
    ).fetchall()

    story_sizes = defaultdict(int)
    story_texts = defaultdict(int)
    by_story = defaultdict(list)
    for r in rows:
        sid = r["story_id"]
        story_sizes[sid] += 1
        if r["has_text"] and r["syndicated_of"] is None:
            story_texts[sid] += 1
        elif r["extract_status"] == "pending" and r["syndicated_of"] is None:
            by_story[sid].append(r)

    raw_by_country = defaultdict(list)
    for sid, arts in by_story.items():
        arts.sort(key=lambda r: (r["id"] == r["representative_article_id"], r["id"]), reverse=True)
        is_multi = story_sizes[sid] >= 2
        base_texts = story_texts[sid]
        for rank_in_story, r in enumerate(arts[:3]):
            eff_texts = base_texts + rank_in_story
            prio = (eff_texts == 0, eff_texts < 2, is_multi, float(r["score"]), r["id"] == r["representative_article_id"], r["id"])
            raw_by_country[r["country"]].append((prio, r))

    by_country = {}
    for c, items in raw_by_country.items():
        items.sort(key=lambda x: x[0], reverse=True)
        dedup = []
        seen = set()
        for prio, r in items:
            if r["id"] not in seen:
                seen.add(r["id"])
                dedup.append((prio, r))
        by_country[c] = dedup

    out = []
    seen_global = set()
    max_len = max((len(v) for v in by_country.values()), default=0)
    for i in range(max_len):
        active = [c for c, lst in by_country.items() if i < len(lst)]
        active.sort(key=lambda c: by_country[c][i][0], reverse=True)
        for c in active:
            r = by_country[c][i][1]
            if r["id"] not in seen_global:
                seen_global.add(r["id"])
                out.append(r)
                if limit and len(out) >= int(limit):
                    return out
    return out


def run(db, limit=None, workers=8, country=None):
    if limit is None and os.environ.get("ARGOS_EXTRACT_LIMIT"):
        limit = int(os.environ["ARGOS_EXTRACT_LIMIT"])
    elif limit is None:
        limit = 250
    country = country or os.environ.get("ARGOS_EXTRACT_COUNTRY")
    story_only = os.environ.get("ARGOS_EXTRACT_STORY_ONLY", "1") != "0"

    rows = _select_pending(db, limit=limit, country=country, story_only=story_only)
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
