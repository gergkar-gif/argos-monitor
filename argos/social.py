"""Stage: auxiliary Telegram and Bluesky signals for crisis & active desks.

Fetches public channel previews (t.me/s/) and open AT Protocol feeds (public.api.bsky.app).
Normalises with NFC (Rule 3) and strips emojis (Rule 7).
Zero API keys or authentication required.
"""
import html
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone

from . import fetch, packs
from .export import SITE_DATA, _write
from .textutil import clean

TG_MSG_RE = re.compile(
    r'data-post="([^"]+)".*?'
    r'<time datetime="([^"]+)".*?'
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL
)


MAX_AGE_HOURS = 168  # 7 days: never surface stale posts from months ago as real-time signals
GLOBAL_CRISIS_TG = ["liveuamap", "insiderpaper"]
GLOBAL_CRISIS_BSKY = [
    "reuters.com", "apnews.com", "afp.com", "aljazeera.com", "bloomberg.com",
    "theguardian.com", "france24.com", "euronews.com", "bellingcat.com", "thediplomat.com",
]


def _clip(text, limit=260):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return (cut or text[:limit]) + "…"


def _is_recent(published, now_dt):
    if not published:
        return False
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now_dt - dt) <= timedelta(hours=MAX_AGE_HOURS)
    except ValueError:
        return False


def _norm_key(text):
    return re.sub(r"[^a-z0-9\u00c0-\u024f\u0400-\u04ff\u1e00-\u1eff]+", "", text.lower())[:64]


def _fetch_telegram(slug, now_dt=None):
    now_dt = now_dt or datetime.now(timezone.utc)
    url = f"https://t.me/s/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf8", errors="ignore")
    except Exception as e:
        print(f"social: tg @{slug} failed: {e}")
        return []

    posts = []
    for m in TG_MSG_RE.finditer(content):
        post_id = m.group(1)
        published = m.group(2)
        if not _is_recent(published, now_dt):
            continue
        raw_text = m.group(3)
        stripped = re.sub(r"<[^>]+>", " ", raw_text)
        cleaned = clean(" ".join(html.unescape(stripped).split()))
        if len(cleaned) < 25 or "trial has expired" in cleaned.lower():
            continue
        posts.append({
            "platform": "telegram",
            "author": f"@{slug}",
            "url": f"https://t.me/{post_id}",
            "published": published,
            "text": _clip(cleaned),
        })
    return posts


def _fetch_bluesky(handle, now_dt=None):
    now_dt = now_dt or datetime.now(timezone.utc)
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&filter=posts_no_replies&limit=15"
    req = urllib.request.Request(url, headers={"User-Agent": "ArgosMonitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf8", errors="ignore"))
    except Exception as e:
        print(f"social: bsky @{handle} failed: {e}")
        return []

    posts = []
    for item in data.get("feed", []):
        if item.get("reason"):
            continue  # skip reposts
        p = item.get("post") or {}
        rec = p.get("record") or {}
        if rec.get("reply"):
            continue
        published = rec.get("createdAt") or ""
        if not _is_recent(published, now_dt):
            continue
        raw_text = rec.get("text") or ""
        cleaned = clean(" ".join(raw_text.split()))
        if len(cleaned) < 25:
            continue
        uri = p.get("uri") or ""
        rkey = uri.split("/")[-1] if uri else ""
        author_handle = (p.get("author") or {}).get("handle") or handle
        posts.append({
            "platform": "bluesky",
            "author": f"@{author_handle}",
            "url": f"https://bsky.app/profile/{author_handle}/post/{rkey}" if rkey else "",
            "published": published,
            "text": _clip(cleaned),
        })
    return posts


def _dedupe_and_cap(pool, limit=8, per_author=5):
    pool = sorted(pool, key=lambda x: x.get("published") or "", reverse=True)
    seen_urls, seen_keys, by_author, out = set(), set(), {}, []
    for item in pool:
        u = item.get("url")
        k = _norm_key(item.get("text", ""))
        auth = item.get("author", "")
        if (u and u in seen_urls) or (k and k in seen_keys):
            continue
        if by_author.get(auth, 0) >= per_author:
            continue
        if u:
            seen_urls.add(u)
        if k:
            seen_keys.add(k)
        by_author[auth] = by_author.get(auth, 0) + 1
        out.append(item)
        if len(out) >= limit:
            break
    return out


def run(db=None):
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    countries = {}

    global_pool = []
    for ch in GLOBAL_CRISIS_TG:
        global_pool.extend(_fetch_telegram(ch, now_dt))
    for ac in GLOBAL_CRISIS_BSKY:
        global_pool.extend(_fetch_bluesky(ac, now_dt))
    print(f"social: fetched {len(global_pool)} recent posts from global crisis/wire monitors")

    for cid in packs.pack_ids():
        pack = packs.load(cid)
        tg_channels = pack.get("telegram") or []
        if isinstance(tg_channels, str):
            tg_channels = [tg_channels]
        bsky_actors = pack.get("bluesky") or []
        if isinstance(bsky_actors, str):
            bsky_actors = [bsky_actors]

        pool = []
        for ch in tg_channels:
            pool.extend(_fetch_telegram(ch, now_dt))
        for ac in bsky_actors:
            pool.extend(_fetch_bluesky(ac, now_dt))

        names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", []), *pack.get("mention", [])]]
        names = [n for n in names if len(n) >= 3]
        if names and global_pool:
            has = lambda text: any(re.search(rf"\b{re.escape(n)}\b", text, re.I) for n in names)
            for p in global_pool:
                if has(p.get("text", "")):
                    pool.append(p)

        deduped = _dedupe_and_cap(pool)
        if deduped:
            countries[cid] = deduped
            print(f"social: {cid}: {len(deduped)} posts collected (TG & Bluesky)")

    payload = {"generated_at": now, "countries": countries}
    _write("social", payload, "ARGOS_SOCIAL")
    print(f"social: saved site/data/social.json with {len(countries)} active desks")
