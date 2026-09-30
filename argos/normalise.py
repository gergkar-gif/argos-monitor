"""Stage 3: content hash and syndication detection (the same text reprinted by different outlets)."""
import hashlib
import re
from collections import defaultdict

SHINGLE = 8       # words per shingle
SAMPLE = 4        # keep 1 in SAMPLE shingle hashes, to keep memory small
THRESHOLD = 0.6   # share of B's sampled shingles found in A => B is a copy of A


def _hashes(text):
    words = re.findall(r"\w+", text.lower())
    out = set()
    for i in range(len(words) - SHINGLE + 1):
        h = int.from_bytes(hashlib.md5(" ".join(words[i:i + SHINGLE]).encode()).digest()[:8], "big")
        if h % SAMPLE == 0:
            out.add(h)
    return out


def run(db):
    rows = db.execute("SELECT id, source_id, text FROM article WHERE text IS NOT NULL "
                      "ORDER BY COALESCE(published_at,'9'), id").fetchall()
    index = defaultdict(set)  # shingle hash -> earlier article ids containing it
    src, marked = {}, 0
    for r in rows:
        db.execute("UPDATE article SET content_hash=?, syndicated_of=NULL WHERE id=?",
                   (hashlib.sha256(r["text"].encode()).hexdigest(), r["id"]))
        hs = _hashes(r["text"])
        src[r["id"]] = r["source_id"]
        if len(hs) < 5:
            continue
        votes = defaultdict(int)
        for h in hs:
            for other in index[h]:
                if src[other] != r["source_id"]:
                    votes[other] += 1
        if votes:
            best, n = max(votes.items(), key=lambda kv: kv[1])
            if n / len(hs) >= THRESHOLD:
                db.execute("UPDATE article SET syndicated_of=? WHERE id=?", (best, r["id"]))
                marked += 1
        for h in hs:
            index[h].add(r["id"])
    db.commit()
    print(f"normalise: {len(rows)} articles hashed, {marked} marked as copies of an earlier article from another outlet")
