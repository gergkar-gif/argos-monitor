"""Stage 5b: what does the story mean for a foreign-office reader? (decision D14)

For each story, find which themes in themes.yaml it touches, by two independent signals:
  keywords    the share of the story's articles whose headline or summary contains one of the theme's keywords;
  similarity  how close the story is to the theme's descriptions, compared with all other stories in its window.
A story gets a theme tag if either signal is strong. The story's policy weight is the highest weight among its
high themes; with only low themes (crime, weather, sport) it gets the lowest of them; with none, the default.
Tags are saved on the story so the page can show why it ranked where it did. No LLM is used.
"""
import json

import numpy as np
import yaml

from .config import ROOT
from .embed import DIM, Embedder

KEYWORD_SHARE = 0.4   # headline-weighted share of a story's articles that must match a theme's keywords
SIM_Z = 4.0           # similarity alone needs this many standard deviations above the window's average story
ALWAYS = {"anticorruption", "security", "diplomacy"}   # themes that stay even on a crime- or accident-flavoured story


def _themes():
    cfg = yaml.safe_load((ROOT / "themes.yaml").read_text(encoding="utf8"))
    return cfg["default_weight"], cfg["themes"]


def _keyword_share(texts, keywords):
    """Share of the story's articles that match: a headline match counts fully, a summary-only match counts 0.3
    (summaries mention common words like "policy" in all sorts of stories, so they can support a tag but not make one)."""
    if not texts:
        return 0.0
    score = 0.0
    for title, lead in texts:
        if any(k in title for k in keywords):
            score += 1.0
        elif any(k in lead for k in keywords):
            score += 0.3
    return score / len(texts)


def run(db):
    default, themes = _themes()
    emb = Embedder()
    protos = []
    for t in themes:
        v = emb.encode(["passage: " + d for d in t["describe"]]).mean(0)
        protos.append(v / np.linalg.norm(v))
    protos = np.array(protos)

    for days, in db.execute("SELECT DISTINCT window_days FROM story").fetchall():
        stories = db.execute("SELECT id FROM story WHERE window_days=?", (days,)).fetchall()
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
    db.commit()
    rows = db.execute("SELECT window_days, COUNT(*), SUM(policy>=0.8), SUM(policy<=0.2) FROM story GROUP BY 1").fetchall()
    for r in rows:
        print(f"policy {r[0]}d: {r[1]} stories; {r[2]} high-weight (>=0.8), {r[3]} low-weight (<=0.2)")
