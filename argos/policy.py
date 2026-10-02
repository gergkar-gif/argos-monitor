"""Stage 5b: what does the story mean for a foreign-office reader? (decision D14)

For each story, find which themes in themes.yaml it touches, by two independent signals:
  keywords    the share of the story's articles whose headline or summary contains one of the theme's keywords;
  similarity  how close the story is to the theme's descriptions, compared with all other stories in its window.
A story gets a theme tag if either signal is strong. The story's policy weight is the highest weight among its
high themes; with only low themes (crime, weather, sport) it gets the lowest of them; with none, the default.
Tags are saved on the story so the page can show why it ranked where it did. No LLM is used.
"""
import json

import re

import numpy as np

from . import packs
from .embed import DIM, Embedder

KEYWORD_SHARE = 0.4   # headline-weighted share of a story's articles that must match a theme's keywords
SIM_Z = 4.0           # similarity alone needs this many standard deviations above the window's average story
ALWAYS = {"anticorruption", "security", "diplomacy"}   # themes that stay even on a crime- or accident-flavoured story


def _matcher(keywords):
    """Short plain-letter keywords ("nato", "gdp", "fdi") match whole words only, otherwise they hit the inside of
    ordinary words ("Bocsánatot" contains "nato"). Longer keywords and stems ("ukrajn") match anywhere."""
    short = [k for k in keywords if k.isascii() and k.replace(" ", "").replace("-", "").isalnum() and len(k) <= 5]
    rest = [k for k in keywords if k not in short]
    pattern_short = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in short) + r")(?!\w)") if short else None
    return lambda text: (pattern_short is not None and bool(pattern_short.search(text))) or any(k in text for k in rest)


def _keyword_share(texts, keywords):
    """Share of the story's articles that match: a headline match counts fully, a summary-only match counts 0.3
    (summaries mention common words like "policy" in all sorts of stories, so they can support a tag but not make one)."""
    if not texts:
        return 0.0
    score = 0.0
    match = _matcher(keywords)
    for title, lead in texts:
        if match(title):
            score += 1.0
        elif match(lead):
            score += 0.3
    return score / len(texts)


def run(db):
    emb = Embedder()
    for country in packs.pack_ids():
        _run_country(db, emb, country)
    db.commit()
    rows = db.execute("SELECT country, window_days, COUNT(*), SUM(policy>=0.8), SUM(policy<=0.2) FROM story GROUP BY 1, 2").fetchall()
    for r in rows:
        print(f"policy {r[0]} {r[1]}d: {r[2]} stories; {r[3]} high-weight (>=0.8), {r[4]} low-weight (<=0.2)")


def _run_country(db, emb, country):
    cfg = packs.load(country)["themes"]
    default, themes = cfg["default_weight"], cfg["themes"]
    protos = []
    for t in themes:
        v = emb.encode(["passage: " + d for d in t["describe"]]).mean(0)
        protos.append(v / np.linalg.norm(v))
    protos = np.array(protos)

    for days, in db.execute("SELECT DISTINCT window_days FROM story WHERE country=?", (country,)).fetchall():
        stories = db.execute("SELECT id FROM story WHERE country=? AND window_days=?", (country, days)).fetchall()
        data = []
        for (sid,) in stories:
            rows = db.execute("SELECT a.title, a.lead, e.vec FROM story_article sa JOIN article a ON a.id=sa.article_id "
                              "JOIN embedding e ON e.article_id=a.id WHERE sa.story_id=?", (sid,)).fetchall()
            if not rows:
                data.append((sid, None, None))
                continue
            centre = np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(len(rows), DIM).mean(0)
            centre /= np.linalg.norm(centre)
            data.append((sid, [(r["title"].lower(), (r["lead"] or "").lower()) for r in rows], centre))
        sims = np.array([protos @ c if c is not None else np.zeros(len(themes)) for _, _, c in data])   # stories x themes
        z = (sims - sims.mean(0)) / (sims.std(0) + 1e-9)

        for i, (sid, texts, _) in enumerate(data):
            kw = {t["id"]: _keyword_share(texts, t["keywords"]) for t in themes}
            tags = [t for j, t in enumerate(themes) if kw[t["id"]] >= KEYWORD_SHARE or z[i, j] >= SIM_Z]
            # A story that reads as an individual crime or accident only counts for themes that a crime story can
            # genuinely signal (the anti-corruption drive, security, diplomacy). A fraud warning is not an investment story.
            lowish = any(t.get("low") and kw[t["id"]] >= KEYWORD_SHARE for t in tags)
            if lowish:
                tags = [t for t in tags if t.get("low") or t["id"] in ALWAYS]
            high = [t for t in tags if not t.get("low")]
            low = [t for t in tags if t.get("low")]
            if high:
                weight = max(t["weight"] for t in high)
            elif low:
                weight = min(t["weight"] for t in low)
            else:
                weight = default
            shown = high or low
            db.execute("UPDATE story SET policy=?, themes=? WHERE id=?",
                       (weight, json.dumps([t["label"] for t in shown], ensure_ascii=False), sid))
            # When the classify stage found no topic, a strong theme decides it: a story tagged Trade is Economy.
            if high and db.execute("SELECT category FROM story WHERE id=?", (sid,)).fetchone()[0] == "other":
                best = max(high, key=lambda t: t["weight"])
                if best.get("category"):
                    db.execute("UPDATE story SET category=? WHERE id=?", (best["category"], sid))
