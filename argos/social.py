"""Stage: auxiliary Telegram and Bluesky signals for crisis & active desks.

Fetches public channel previews (t.me/s/) and open AT Protocol feeds (public.api.bsky.app).
Normalises with NFC (Rule 3) and strips emojis (Rule 7).
Zero API keys or authentication required.
"""
import html
import json
import re
import urllib.request
from datetime import datetime, timezone

from . import fetch, packs
from .export import SITE_DATA, _write
from .textutil import clean

TG_MSG_RE = re.compile(
    r'data-post="([^"]+)".*?'
    r'<time datetime="([^"]+)".*?'
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL
)


def _fetch_telegram(slug):
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
        raw_text = m.group(3)
        stripped = re.sub(r"<[^>]+>", " ", raw_text)
        cleaned = clean(" ".join(html.unescape(stripped).split()))
        if len(cleaned) < 25:
            continue
        posts.append({
            "platform": "telegram",
            "author": f"@{slug}",
            "url": f"https://t.me/{post_id}",
            "published": published,
            "text": cleaned[:280]
        })
    return posts


def _fetch_bluesky(handle):
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit=12"
    req = urllib.request.Request(url, headers={"User-Agent": "ArgosMonitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf8", errors="ignore"))
    except Exception as e:
        print(f"social: bsky @{handle} failed: {e}")
        return []

    posts = []
    for item in data.get("feed", []):
        p = item.get("post") or {}
        rec = p.get("record") or {}
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
            "published": rec.get("createdAt") or "",
            "text": cleaned[:280]
        })
    return posts


def run(db=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    countries = {}

    for cid in packs.pack_ids():
        pack = packs.load(cid)
        tg_channels = pack.get("telegram") or []
        if isinstance(tg_channels, str):
            tg_channels = [tg_channels]
        bsky_actors = pack.get("bluesky") or []
        if isinstance(bsky_actors, str):
            bsky_actors = [bsky_actors]

        if not tg_channels and not bsky_actors:
            continue

        pool = []
        for ch in tg_channels:
            pool.extend(_fetch_telegram(ch))
        for ac in bsky_actors:
            pool.extend(_fetch_bluesky(ac))

        if pool:
            pool.sort(key=lambda x: x.get("published") or "", reverse=True)
            countries[cid] = pool[:10]
            print(f"social: {cid}: {len(countries[cid])} posts collected (TG & Bluesky)")

    payload = {"generated_at": now, "countries": countries}
    _write("social", payload, "ARGOS_SOCIAL")
    print(f"social: saved site/data/social.json with {len(countries)} active desks")
