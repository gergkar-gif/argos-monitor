"""Stage 3: content hash and syndication detection (the same text reprinted by different outlets).
Guarantees independent source counts (Rule 5) by detecting exact and near-duplicate wire copies."""
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .ingest import title_key

SHINGLE = 8       # words per shingle
SAMPLE = 4        # keep 1 in SAMPLE shingle hashes, to keep memory small
THRESHOLD = 0.6   # share of B's sampled shingles found in A => B is a copy of A
WIRE_THRESHOLD = 0.35  # lower threshold when text explicitly credits a wire agency

# Explicit wire attribution markers commonly used in syndicated press copy
WIRE_CREDIT_RE = re.compile(
    r"\b(?:theo\s+ttxvn|nguồn:\s*ttxvn|\(ttxvn\)|theo\s+vna|\(vna\)|"
    r"selon\s+l'aps|\(aps\)|\(belta\)|\(белта\)|\(тасс\)|\(ria\s+novosti\)|\(риа\s+новости\)|"
    r"\(reuters\)|\(ap\)|\(afp\)|\bafp\b|\breuters\b)\b",
    re.I
)


def _hashes(text):
    words = re.findall(r"\w+", text.lower())
    out = set()
    for i in range(len(words) - SHINGLE + 1):
        h = int.from_bytes(hashlib.md5(" ".join(words[i:i + SHINGLE]).encode()).digest()[:8], "big")
        if h % SAMPLE == 0:
            out.add(h)
    return out


def run(db):
    cols = {r[1] for r in db.execute("PRAGMA table_info(article)")}
    has_country = "country" in cols
    has_fetched = "fetched_at" in cols
    cutoff_10d = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
    country_sel = "country" if has_country else "'' AS country"
    if has_fetched:
        rows = db.execute(
            f"SELECT id, {country_sel}, source_id, title, lead, text FROM article "
            "WHERE (text IS NOT NULL OR lead IS NOT NULL) "
            "AND (content_hash IS NULL OR COALESCE(published_at, fetched_at, '9') >= ?) "
            "ORDER BY COALESCE(published_at, fetched_at, '9'), id",
            (cutoff_10d,),
        ).fetchall()
    else:
        rows = db.execute(
            f"SELECT id, {country_sel}, source_id, title, lead, text FROM article "
            "WHERE text IS NOT NULL OR lead IS NOT NULL "
            "ORDER BY COALESCE(published_at,'9'), id"
        ).fetchall()
    # Cache source kinds for wire attribution (including MTI, Tanjug, Agerpres, TASR, HINA, STA, BTA)
    wire_sources = {r[0] for r in db.execute("SELECT id FROM source WHERE kind='wire' OR state_affiliated=1").fetchall()}
    index = defaultdict(set)  # (country, shingle hash) -> earlier article ids containing it
    src, marked = {}, 0
    for r in rows:
        cid = r["country"] or ""
        content = r["text"] or (r["title"] + " " + (r["lead"] or ""))
        db.execute("UPDATE article SET content_hash=?, syndicated_of=NULL WHERE id=?",
                   (hashlib.sha256(content.encode()).hexdigest(), r["id"]))
        hs = _hashes(content)
        src[r["id"]] = r["source_id"]
        if len(hs) < 5:
            continue
        votes = defaultdict(int)
        for h in hs:
            for other in index[(cid, h)]:
                if src[other] != r["source_id"]:
                    votes[other] += 1
        if votes:
            best, n = max(votes.items(), key=lambda kv: kv[1])
            is_wire = src[best] in wire_sources or WIRE_CREDIT_RE.search(content)
            req_threshold = WIRE_THRESHOLD if is_wire else THRESHOLD
            if n / len(hs) >= req_threshold:
                db.execute("UPDATE article SET syndicated_of=? WHERE id=?", (best, r["id"]))
                marked += 1
        for h in hs:
            index[(cid, h)].add(r["id"])

    # Headline-only articles (aggregator items) have no text to compare. The same headline from different outlets
    # within the same country desk is one wire story reprinted, so it counts once.
    if has_fetched:
        db.execute("UPDATE article SET syndicated_of=NULL WHERE extract_status='nofetch' AND COALESCE(published_at, fetched_at, '9') >= ?", (cutoff_10d,))
        nofetch_rows = db.execute(
            f"SELECT id, {country_sel}, source_id, title FROM article "
            "WHERE extract_status='nofetch' AND COALESCE(published_at, fetched_at, '9') >= ? "
            "ORDER BY COALESCE(published_at, fetched_at, '9'), id",
            (cutoff_10d,),
        ).fetchall()
    else:
        db.execute("UPDATE article SET syndicated_of=NULL WHERE extract_status='nofetch'")
        nofetch_rows = db.execute(
            f"SELECT id, {country_sel}, source_id, title FROM article WHERE extract_status='nofetch' "
            "ORDER BY COALESCE(published_at,'9'), id"
        ).fetchall()
    first = {}
    for r in nofetch_rows:
        key = (r["country"] or "", title_key(r["title"]))
        if key in first and first[key][1] != r["source_id"]:
            db.execute("UPDATE article SET syndicated_of=? WHERE id=?", (first[key][0], r["id"]))
            marked += 1
        else:
            first.setdefault(key, (r["id"], r["source_id"]))
    db.commit()
    print(f"normalise: {len(rows)} articles hashed, {marked} marked as copies of an earlier article from another outlet")
