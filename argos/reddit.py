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
    r"english teaching|noise complain|where can i buy|looking for friends|rate my|shitpost|ama|ask me anything|"
    r"e-?visa|return ticket|postcards|dna test)\b|^i want\b)",
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
    r = pack.get("reddit") or []
    return [r] if isinstance(r, str) else list(r)


def _clean_body(e):
    raw = e.get("summary") or (e.get("content") or [{}])[0].get("value") or ""
    txt = FOOT_RE.sub("", TAG_RE.sub(" ", html.unescape(raw)))
    return " ".join(txt.split())


def _post(e):
    m = SUB_RE.search(e.get("link") or "")
    return {"title": (e.get("title") or "").strip(), "body": _clean_body(e), "url": e.get("link") or "", "sub": m.group(1) if m else ""}


def _filter_country(cid, raw_posts, emb, noise_vecs):
    if not raw_posts:
        return []
    themes = packs.load(cid)["themes"]["themes"]
    protos = np.array([
        (v := emb.encode(["passage: " + d for d in t["describe"]]).mean(0)) / np.linalg.norm(v)
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
        title_low = p["title"].lower()
        kw_hits = [t for t in themes if matchers[t["id"]](title_low)]
        sims = protos @ vec
        noise_sim = float(np.max(noise_vecs @ vec))
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_theme = themes[best_idx]

        # Without a keyword match, drop open-ended questions (tourist/personal Q&A) and require a substantive
        # statement (>= 6 words) with strong theme similarity (>= 0.815) that beats the noise prototypes.
        if kw_hits:
            chosen = max(kw_hits, key=lambda t: t.get("weight", 0.5))
        else:
            if p["title"].strip().endswith("?") or len(p["title"].split()) < 6 or best_sim < 0.815 or best_sim <= noise_sim + 0.015:
                continue
            chosen = best_theme

        kept.append((
            bool(kw_hits),
            chosen.get("weight", 0.5),
            {
                "title": p["title"],
                "url": p["url"],
                "sub": p["sub"],
                "tag": chosen.get("label") or chosen["id"].replace("_", " ").title(),
            },
        ))
    kept.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in kept[:POSTS]]


def run(db=None):
    emb = Embedder()
    noise_vecs = emb.encode(["passage: " + t for t in NOISE_TEXTS])
    noise_vecs = noise_vecs / np.linalg.norm(noise_vecs, axis=1, keepdims=True)

    by_country = {cid: _subs(packs.load(cid)) for cid in packs.pack_ids()}
    owner = {s.lower(): cid for cid, subs in by_country.items() for s in subs}
    out = {}
    all_subs = "+".join(s for subs in by_country.values() for s in subs)
    status, body = fetch.get(URL.format(all_subs)) if all_subs else (0, b"")
    if status == 429:
        time.sleep(60)
        status, body = fetch.get(URL.format(all_subs))
    buckets = {cid: [] for cid in by_country}
    if status == 200:
        for e in feedparser.parse(body).entries:
            p = _post(e)
            cid = owner.get(p["sub"].lower())
            if cid:
                buckets[cid].append(p)
        for cid, subs in by_country.items():
            kept = _filter_country(cid, buckets[cid], emb, noise_vecs)
            if len(kept) >= 3:
                out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in subs), "posts": kept}
                print(f"reddit: {cid}: {len(kept)}/{len(buckets[cid])} desk-relevant posts across {out[cid]['subreddit']}")
    # Second batch: combine remaining countries into one multireddit request so smaller subs aren't crowded out by giant ones.
    rem = [cid for cid, subs in by_country.items() if cid not in out and subs]
    if rem:
        rem_subs = "+".join(s for cid in rem for s in by_country[cid])
        status, body = fetch.get(URL.format(rem_subs))
        if status == 429:
            time.sleep(60)
            status, body = fetch.get(URL.format(rem_subs))
        if status == 200:
            for e in feedparser.parse(body).entries:
                p = _post(e)
                cid = owner.get(p["sub"].lower())
                if cid in rem and p["url"] not in {x["url"] for x in buckets[cid]}:
                    buckets[cid].append(p)
            for cid in list(rem):
                kept = _filter_country(cid, buckets[cid], emb, noise_vecs)
                if len(kept) >= 2:
                    out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in by_country[cid]), "posts": kept}
                    print(f"reddit: {cid}: {len(kept)}/{len(buckets[cid])} desk-relevant posts across {out[cid]['subreddit']}")
                    rem.remove(cid)
    # Final fallback for very low-volume country subreddits (week window, combined).
    if rem:
        rem_subs = "+".join(s for cid in rem for s in by_country[cid])
        status, body = fetch.get(WEEK_URL.format(rem_subs))
        if status == 200:
            for e in feedparser.parse(body).entries:
                p = _post(e)
                cid = owner.get(p["sub"].lower())
                if cid in rem and p["url"] not in {x["url"] for x in buckets[cid]}:
                    buckets[cid].append(p)
        for cid in rem:
            kept = _filter_country(cid, buckets[cid], emb, noise_vecs)
            if kept:
                out[cid] = {"subreddit": ", ".join(f"r/{s}" for s in by_country[cid]), "posts": kept}
                print(f"reddit: {cid}: {len(kept)}/{len(buckets[cid])} desk-relevant posts across {out[cid]['subreddit']}")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("reddit", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_REDDIT")

