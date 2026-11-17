"""Stage: auxiliary Telegram signals for crisis & active desks.

Fetches public channel previews (t.me/s/).
Normalises with NFC (Rule 3) and strips emojis (Rule 7).
Zero API keys or authentication required.
"""
import html
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import packs
from .export import SITE_DATA, _write
from .textutil import clean

TG_MSG_RE = re.compile(
    r'data-post="([^"]+)".*?'
    r'<time datetime="([^"]+)".*?'
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL
)


MAX_AGE_HOURS = 168  # 7 days: never surface stale posts from months ago as real-time signals
GLOBAL_CRISIS_TG = ["liveuamap"]


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

    pack_list = []
    all_channels = list(GLOBAL_CRISIS_TG)
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        tgs = pack.get("telegram") or []
        if isinstance(tgs, str):
            tgs = [tgs]
        pack_list.append((cid, pack, tgs))
        all_channels.extend(tgs)

    unique_channels = list(dict.fromkeys(all_channels))
    with ThreadPoolExecutor(max_workers=8) as ex:
        fetched = dict(zip(unique_channels, ex.map(lambda ch: _fetch_telegram(ch, now_dt), unique_channels)))

    global_pool = [p for ch in GLOBAL_CRISIS_TG for p in fetched.get(ch, [])]
    print(f"social: fetched {len(global_pool)} recent posts from global Telegram crisis monitors")

    for cid, pack, tg_channels in pack_list:
        pool = [p for ch in tg_channels for p in fetched.get(ch, [])]

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
            print(f"social: {cid}: {len(deduped)} posts collected (Telegram)")

    payload = {"generated_at": now, "countries": countries}
    _write("social", payload, "ARGOS_SOCIAL")
    print(f"social: saved site/data/social.json with {len(countries)} active desks")
