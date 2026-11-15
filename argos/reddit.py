"""Stage: what people talk about on the country's subreddits today (top posts of the day, via Reddit's public RSS).

Supports a list of subreddits per country in pack.yaml (e.g. [Vietnam, vozforums, TroChuyenLinhTinh, hanoi, Saigon]),
filters out personal/tourist/meme noise using the country's foreign-desk themes (themes.yaml) and multilingual embeddings,
and batches requests to respect Reddit's IP rate limit.
"""
import html
import re
import time
from datetime import datetime, timezone

import feedparser
import numpy as np

from . import fetch, packs, policy
from .embed import Embedder
from .export import SITE_DATA, _write
from .textutil import clean

URL = "https://www.reddit.com/r/{}/top/.rss?t=day&limit=100"
WEEK_URL = "https://www.reddit.com/r/{}/top/.rss?t=week&limit=100"
POSTS = 6
SUB_RE = re.compile(r"/r/([^/]+)/")
TAG_RE = re.compile(r"<[^>]+>")
FOOT_RE = re.compile(r"(?:&#32;)?\s*submitted by\s+/u/\S+.*", re.I | re.S)

# Non-desk Reddit noise (personal anecdotes, tourist/expat Q&A, nightlife, pets/wildlife photos, vague clickbait).
NOISE_TEXTS = [
    "personal story, my friend died, family memory, grief, relationship advice, dating, girlfriend, boyfriend",
    "tourist question, question for locals, travel itinerary, hotel, restaurant, clubbing, nightlife, where to buy",
    "cute animal, pet, dog, cat, bird, owl in the city, nature photo, sunset, street photo, meme, joke",
    "what is this called, oh the irony, this should be illegal, look at this, random question, halloween candy",
]
FLUFF_RE = re.compile(
    r"(\[removed|removed by reddit|\b(?:what is this called|question for|oh the irony|this should be illegal|"
    r"clubbing|dating|tinder|bumble|itinerary|first time visiting|what would you recommend|what can i skip|"
    r"recommendations|advice needed|planning to move|need help looking for|can i make an|getting back into|"
    r"english teaching|teach english|noise complain|where can i buy|looking for friends|rate my|shitpost|ama|ask me anything|"
    r"e-?visa|visa run|return ticket|postcards|dna test|tipping|sim card|layover|digital nomad|"
    r"where to stay|best restaurant|best coffee|unpopular opinion|shower thought|am i the asshole|aita)\b|^i want\b)",
    re.I,
)
# Extra civic/political/economic terms often used in Reddit discussions (supplementing themes.yaml keywords).
CIVIC_EXTRA = {
    "econ_policy": [
        "prices", "cost of living", "rent", "salary", "wages", "tax", "taxes", "property", "housing",
        "fizetés", "albérlet", "drágulás", "árak", "lương", "giá nhà", "thuế", "តម្លៃ", "ពន្ធ", "កម្មករ",
    ],
    "party_gov": [
        "magyar péter", "orbán", "mészáros", "várkonyi", "fidelitas", "tisza", "kormány", "polgármester",
        "councillor", "municipality", "afriforum", "politician", "minister", "government", "protest",
        "bộ công an", "đại biểu", "cộng sản",
    ],
    "anticorruption": ["lavish", "taxpayer", "oligarch", "magángép", "ner", "közpénz", "bribe", "scandal"],
    "accident_weather": ["stranded", "cruise ship", "typhoon", "cyclone", "power outage", "blackout"],
}


def _subs(pack):
    r = pack.get("reddit") or pack.get("subreddits") or []
    return [r] if isinstance(r, str) else list(r)


def _clean_body(e):
    raw = e.get("summary") or (e.get("content") or [{}])[0].get("value") or ""
    txt = FOOT_RE.sub("", TAG_RE.sub(" ", html.unescape(raw)))
    return clean(txt)


def _iso_time(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    if not t:
        return ""
    return datetime(*t[:6], tzinfo=timezone.utc).isoformat(timespec="seconds")


def _post(e):
    m = SUB_RE.search(e.get("link") or "")
    return {
        "title": clean(e.get("title")),
        "body": _clean_body(e),
        "url": e.get("link") or "",
        "sub": m.group(1) if m else "",
        "published": _iso_time(e),
    }


def _filter_country(cid, raw_posts, emb, noise_vecs):
    if not raw_posts:
        return []
    themes = packs.load(cid)["themes"]["themes"]
    protos = np.array([
        (v := emb.encode(["passage: " + d for d in (t.get("describe") or [t["label"]])]).mean(0)) / np.linalg.norm(v)
        for t in themes
    ])
    matchers = {
        t["id"]: policy._matcher(list(t["keywords"]) + CIVIC_EXTRA.get(t["id"], []))
        for t in themes
    }

    candidates = []
    for p in raw_posts:
        title = p["title"]
        if not title or FLUFF_RE.search(title):
            continue
        candidates.append(p)
    if not candidates:
        return []

    texts = [f"query: {p['title']}" for p in candidates]
    vecs = emb.encode(texts)

    kept = []
    for p, vec in zip(candidates, vecs):
        blob_low = f"{p['title']} {p['body'][:240]}".lower()
        kw_hits = [t for t in themes if matchers[t["id"]](blob_low)]
        sims = protos @ vec
        noise_sim = float(np.max(noise_vecs @ vec))
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_theme = themes[best_idx]

        # Without a keyword match, drop open-ended questions (tourist/personal Q&A) and require a substantive
        # statement (>= 6 words) with strong theme similarity (>= 0.785) that clearly beats the noise prototypes.
        if kw_hits:
            chosen = max(kw_hits, key=lambda t: t.get("weight", 0.5))
        else:
            if p["title"].strip().endswith("?") or len(p["title"].split()) < 6 or best_sim < 0.785 or best_sim <= noise_sim + 0.02:
                continue
            chosen = best_theme

        kept.append((
            bool(kw_hits),
            chosen.get("weight", 0.5),
            best_sim,
            {
                "title": p["title"],
                "url": p["url"],
                "sub": p["sub"],
                "published": p.get("published") or "",
                "tag": chosen.get("label") or chosen["id"].replace("_", " ").title(),
            },
        ))
    kept.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [x[3] for x in kept[:POSTS]]


def _chunk_countries(cids, by_country, max_countries=6, max_subs=18):
    """Group countries into small multireddit batches so high-volume subs don't crowd out smaller desks."""
    batch, sub_count = [], 0
    for cid in cids:
        subs = by_country[cid]
        if not subs:
            continue
        if batch and (len(batch) >= max_countries or sub_count + len(subs) > max_subs):
            yield batch
            batch, sub_count = [], 0
        batch.append(cid)
        sub_count += len(subs)
    if batch:
        yield batch


def _fetch_batch(url_tmpl, subs):
    status, body = fetch.get(url_tmpl.format("+".join(subs)))
    if status == 429:
        time.sleep(30)
        status, body = fetch.get(url_tmpl.format("+".join(subs)))
    return feedparser.parse(body).entries if status == 200 else []


def run(db=None):
    try:
        emb = Embedder()
        noise_vecs = emb.encode(["passage: " + t for t in NOISE_TEXTS])
        noise_vecs = noise_vecs / np.linalg.norm(noise_vecs, axis=1, keepdims=True)
    except Exception as e:
        print(f"reddit: skipping due to missing model or embedding initialization error: {e}")
        return

    by_country = {cid: _subs(packs.load(cid)) for cid in packs.pack_ids()}
    owner = {s.lower(): cid for cid, subs in by_country.items() for s in subs}
    buckets = {cid: [] for cid in by_country}
    seen_urls = {cid: set() for cid in by_country}
    out = {}

    def ingest_entries(entries, allowed):
        for e in entries:
            p = _post(e)
            cid = owner.get(p["sub"].lower())
            if cid in allowed and p["url"] not in seen_urls[cid]:
                seen_urls[cid].add(p["url"])
                buckets[cid].append(p)

    # Pass 1: top posts of the day, fetched in small country chunks so no desk is starved.
    active = [cid for cid, subs in by_country.items() if subs]
    for i, batch in enumerate(_chunk_countries(active, by_country)):
        if i:
            time.sleep(2.2)
        subs = [s for cid in batch for s in by_country[cid]]
        ingest_entries(_fetch_batch(URL, subs), set(batch))

    rem = []
    for cid in active:
        kept = _filter_country(cid, buckets[cid], emb, noise_vecs)
        if len(kept) >= 2:
            out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in by_country[cid]), "posts": kept}
            print(f"reddit: {cid}: {len(kept)}/{len(buckets[cid])} desk-relevant posts across {out[cid]['subreddit']}")
        else:
            rem.append(cid)

    # Pass 2: top posts of the week (chunked) for low-volume desks that had < 2 relevant posts today.
    for i, batch in enumerate(_chunk_countries(rem, by_country)):
        time.sleep(2.2)
        subs = [s for cid in batch for s in by_country[cid]]
        ingest_entries(_fetch_batch(WEEK_URL, subs), set(batch))
    for cid in rem:
        kept = _filter_country(cid, buckets[cid], emb, noise_vecs)
        if kept:
            out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in by_country[cid]), "posts": kept}
            print(f"reddit: {cid}: {len(kept)}/{len(buckets[cid])} desk-relevant posts (week) across {out[cid]['subreddit']}")

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("reddit", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_REDDIT")

