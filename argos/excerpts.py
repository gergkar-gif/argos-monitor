"""Stage 6b: choose quoted sentences for each dashboard story, and verify them.

An excerpt is a sentence copied character for character from a stored article. Each row records where
in the article it came from (char_start, char_end), so `verify` can prove text == article.text[start:end].
This is the audit trail for "no source, no statement".
"""
import re

import numpy as np

from .embed import DIM, Embedder
from .rank import dashboard_story_ids

MAX_EXCERPTS = 3
MIN_LEN, MAX_LEN = 60, 320
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
DATELINE = re.compile(r"^\s*(?:[\w.]+\.vn|VOV|VNA|TTXVN|Hà Nội \(TTXVN\)|[\w\s]{2,25}\((?:TTXVN|VNA)\))\s*[-–—]\s*", re.I)
NOISE =re.compile(r"^(ảnh|video|clip|xem thêm|đọc thêm|photo|theo |nguồn|\(|\[)", re.I)


def _glued_place(part):
    """Offset where the real sentence starts when a capitalised place name (1 to 3 words) is fused to it, else 0."""
    for i in range(3, min(len(part) - 1, 24)):
        if part[i].islower() and part[i + 1].isupper():
            words = part[:i + 1].split(" ")
            if len(words) >= 2 and all(w[:1].isupper() for w in words):
                return i + 1
            return 0
    return 0


def sentences(text, first_n=8):
    """Yield (start, end) offsets of the first sentences of an article, skipping the title line."""
    found = []
    lines = list(re.finditer(r"[^\n]+", text))
    for line in lines[1:]:                       # line 0 is the headline repeated by the extractor
        pos = line.start()
        for part in SENTENCE_END.split(line.group()):
            start = text.index(part, pos)
            pos = start + len(part)
            lead = len(part) - len(part.lstrip())     # leading indentation is not part of the sentence
            start, part = start + lead, part.lstrip()
            cut = _glued_place(part)                  # "Đồng NaiHành khách..." -> the extractor glued a place name on
            start, part = start + cut, part[cut:]
            tag = DATELINE.match(part)            # drop "VOV.VN -" style bylines: still a verbatim substring
            if tag:
                start += tag.end()
                part = part[tag.end():]
            if MIN_LEN <= len(part) <= MAX_LEN and not NOISE.match(part) and part[-1] in ".!?…\"”":
                found.append((start, start + len(part)))
        if len(found) >= first_n:
            break
    return found[:first_n]


def run(db):
    ids = dashboard_story_ids(db)
    emb = Embedder()
    db.execute("DELETE FROM excerpt")
    total = 0
    for sid in ids:
        arts = db.execute(
            "SELECT a.id, a.source_id, a.text, s.scope, e.vec FROM story_article sa JOIN article a ON a.id=sa.article_id "
            "JOIN source s ON s.id=a.source_id JOIN embedding e ON e.article_id=a.id "
            "WHERE sa.story_id=? AND a.text IS NOT NULL AND a.syndicated_of IS NULL", (sid,)).fetchall()
        if not arts:
            continue
        centre = np.frombuffer(b"".join(a["vec"] for a in arts), dtype=np.float32).reshape(len(arts), DIM).mean(0)
        centre /= np.linalg.norm(centre)
        best_per_source = {}
        for a in arts:
            spans = sentences(a["text"])
            if not spans:
                continue
            vecs = emb.encode(["passage: " + a["text"][s:e] for s, e in spans])
            k = int(np.argmax(vecs @ centre))
            score = float(vecs[k] @ centre)
            if a["source_id"] not in best_per_source or score > best_per_source[a["source_id"]][0]:
                best_per_source[a["source_id"]] = (score, a["id"], spans[k], a["scope"])
        # one sentence per source, best first, preferring a mix of scopes
        ranked = sorted(best_per_source.values(), key=lambda c: -c[0])
        chosen = []
        for scope in dict.fromkeys(c[3] for c in ranked):          # best candidate of each scope first
            chosen.append(next(c for c in ranked if c[3] == scope))
        chosen = chosen[:MAX_EXCERPTS]
        chosen += [c for c in ranked if c not in chosen][:MAX_EXCERPTS - len(chosen)]
        for _, aid, (s, e), _ in chosen:
            text = db.execute("SELECT text FROM article WHERE id=?", (aid,)).fetchone()[0]
            db.execute("INSERT INTO excerpt (story_id, article_id, text, char_start, char_end) VALUES (?,?,?,?,?)",
                       (sid, aid, text[s:e], s, e))
            total += 1
    db.commit()
    print(f"excerpts: {total} excerpts chosen for {len(ids)} stories")


def verify(db):
    """Check every excerpt equals the stored article text at its recorded position."""
    bad = 0
    rows = db.execute("SELECT x.id, x.text, x.char_start, x.char_end, a.text AS full FROM excerpt x "
                      "JOIN article a ON a.id=x.article_id").fetchall()
    for r in rows:
        if r["full"][r["char_start"]:r["char_end"]] != r["text"]:
            bad += 1
            print(f"  MISMATCH excerpt {r['id']}")
    print(f"verify: {len(rows) - bad}/{len(rows)} excerpts match their article text exactly")
    return bad == 0
