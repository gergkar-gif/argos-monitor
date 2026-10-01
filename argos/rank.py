"""Stage 5b: score stories. Syndicated copies count once (rule 5).

coverage = independent sources
         + 0.5 per extra coverage type beyond the first (domestic / abroad_local / international)
         + 1 if the story is growing (at least 40% of its articles are from the last 24 hours)
         + 0.2 * log2(articles)   -- a small tie-breaker for volume

score = coverage * (0.4 + 0.8 * policy) + 3 * policy

`policy` (0 to 1) is how much the story matters to a foreign-office reader: diplomacy, trade, investment and
policy weigh most, individual crimes, accidents and weather least (see policy.py and themes.yaml, decision D14).
A well-covered story with no policy angle therefore falls behind a smaller policy story.
"""
import math
from datetime import datetime, timedelta, timezone


def dashboard_story_ids(db, country=None, window_days=None, n=10, per_category=12):
    """Stories the site shows for a country and window: the top n overall plus the top few in each category.
    With no country or window given, the union over every one."""
    where, args = [], []
    if country:
        where.append("country=?"); args.append(country)
    if window_days:
        where.append("window_days=?"); args.append(window_days)
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    ids = []
    for c, w in db.execute(f"SELECT DISTINCT country, window_days FROM story{cond}", args).fetchall():
        ids += [r[0] for r in db.execute("SELECT id FROM story WHERE country=? AND window_days=? ORDER BY score DESC LIMIT ?", (c, w, n))]
        for (cat,) in db.execute("SELECT DISTINCT category FROM story WHERE country=? AND window_days=?", (c, w)).fetchall():
            ids += [r[0] for r in db.execute(
                "SELECT id FROM story WHERE country=? AND window_days=? AND category=? ORDER BY score DESC LIMIT ?", (c, w, cat, per_category))]
    return list(dict.fromkeys(ids))


def run(db):
    recent = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    for sid, in db.execute("SELECT id FROM story").fetchall():
        rows = db.execute(
            "SELECT a.source_id, a.syndicated_of, COALESCE(a.published_at, a.fetched_at) t, s.scope, s.kind "
            "FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source s ON s.id=a.source_id "
            "WHERE sa.story_id=?", (sid,)).fetchall()
        independent = {r["source_id"] for r in rows if r["syndicated_of"] is None}
        scopes = {r["scope"] for r in rows}
        growing = sum(r["t"] >= recent for r in rows) / len(rows) >= 0.4
        coverage = (len(independent) + 0.5 * (len(scopes) - 1) + (1.0 if growing else 0.0)
                    + 0.2 * math.log2(len(rows)))
        policy = db.execute("SELECT policy FROM story WHERE id=?", (sid,)).fetchone()[0]
        policy = 0.3 if policy is None else policy
        score = coverage * (0.4 + 0.8 * policy) + 3 * policy
        db.execute("UPDATE story SET score=? WHERE id=?", (round(score, 2), sid))
    db.commit()
    print("rank: scored", db.execute("SELECT COUNT(*) FROM story").fetchone()[0], "stories")
