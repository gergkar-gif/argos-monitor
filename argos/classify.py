"""Stage 5a: give each story a category (decision D8: section feeds first, then embeddings).

1. If most of a story's articles come from an economics, foreign-policy or defence-security section
   feed, the story gets that category. Those sections are reliable.
2. Otherwise (catch-all sections, or no section) the story is compared with a short description of each
   category, using the same embedding model: English wording shared by all countries, plus the country's
   own wording in its language (classify: in its pack.yaml).
3. If nothing is close enough, the category is 'other'.
"""
from collections import Counter

import numpy as np

from . import packs
from .embed import DIM, Embedder

RELIABLE = ("economics", "foreign_policy", "defence_security")
SECTION_SHARE = 0.5     # share of a story's articles needed for a section hint to decide
MIN_SIMILARITY = 0.80   # below this, a story fits no category description

DESCRIPTIONS = {
    "internal_politics": [
        "ruling party, parliament, government, ministers, appointments, discipline of officials, anti-corruption, elections, new laws",
        "country politics, party leadership, personnel changes, parliament session, resolutions",
    ],
    "economics": [
        "the economy, GDP growth, inflation, interest rates, banks, gold price, fuel price, stock market, exchange rate",
        "companies, investment, exports and imports, trade, taxes, infrastructure projects, real estate, jobs and wages",
    ],
    "foreign_policy": [
        "diplomatic relations, state visit, bilateral talks, agreements, strategic partnership, ambassadors, summits",
        "relations with the European Union, the United States, China, Russia, ASEAN or neighbouring countries, sanctions",
    ],
    "defence_security": [
        "military, defence ministry, armed forces, exercises, border guards, intelligence, cybersecurity, terrorism, national security",
    ],
    "society": [
        "education, schools, health care, hospitals, disease, vaccines, pensions, social issues",
        "traffic accidents, natural disasters, storms, weather, environment, crime, court cases, arrests, daily life",
        "society, culture, sports, tourism, local news",
    ],
}


def _prototypes(emb, country):
    local = packs.load(country).get("classify") or {}
    names, vecs = [], []
    for cat, texts in DESCRIPTIONS.items():
        v = emb.encode(["passage: " + t for t in texts + local.get(cat, [])]).mean(0)
        names.append(cat)
        vecs.append(v / np.linalg.norm(v))
    return names, np.array(vecs)


def run(db, min_similarity=MIN_SIMILARITY):
    emb = Embedder()
    counts, sims = Counter(), []
    for country in packs.pack_ids():
        names, protos = _prototypes(emb, country)
        for (sid,) in db.execute("SELECT id FROM story WHERE country=?", (country,)).fetchall():
            rows = db.execute("SELECT f.category_hint, e.vec FROM story_article sa JOIN article a ON a.id=sa.article_id "
                              "JOIN embedding e ON e.article_id=a.id LEFT JOIN feed f ON f.id=a.feed_id "
                              "WHERE sa.story_id=?", (sid,)).fetchall()
            hints = Counter(r["category_hint"] for r in rows if r["category_hint"] in RELIABLE)
            top, n = hints.most_common(1)[0] if hints else (None, 0)
            if top and n / len(rows) >= SECTION_SHARE:
                cat = top
            else:
                centroid = np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(len(rows), DIM).mean(0)
                centroid /= np.linalg.norm(centroid)
                s = protos @ centroid
                best = int(np.argmax(s))
                sims.append(float(s[best]))
                cat = names[best] if s[best] >= min_similarity else "other"
            db.execute("UPDATE story SET category=? WHERE id=?", (cat, sid))
            counts[(country, cat)] += 1
    db.commit()
    for country in packs.pack_ids():
        print(f"classify {country}:", {c: n for (k, c), n in counts.items() if k == country})
    if sims:
        print(f"  embedding-classified stories: {len(sims)}, similarity to best category: "
              f"median {np.median(sims):.3f}, 10th percentile {np.percentile(sims, 10):.3f}")
