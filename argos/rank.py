"""Stage 5b: score stories. Syndicated copies count once (rule 5).

coverage = independent sources
         + consensus bonus (+1.0 for 3+ independent sources, +2.0 + 0.5*(n-5) for 5+)
         + 0.5 per extra coverage type beyond the first (domestic / abroad_local / international)
         + 1 if the story is growing (at least 40% of its articles are from the last 24 hours)
         + 0.2 * log2(articles)   -- a small tie-breaker for volume

score = coverage * (0.6 + 0.5 * policy) + 1.2 * policy + (2.5 if election)

`policy` (0 to 1) is how much the story matters to a foreign-office reader: diplomacy, trade, investment and
policy weigh most, individual crimes, accidents and weather least (see policy.py and themes.yaml, decision D14).
A high-consensus multi-outlet national story reliably outranks a single-outlet item with an accidental keyword hit.
"""
import math
from datetime import datetime, timedelta, timezone

from . import packs


def dashboard_story_ids(db, country=None, window_days=None, n=None, per_category=None):
    """Stories the site shows for a country and window.
    With n and per_category omitted (default), returns all stories for the window ordered by score."""
    where, args = [], []
    if country:
        where.append("country=?"); args.append(country)
    if window_days:
        where.append("window_days=?"); args.append(window_days)
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    if n is None and per_category is None:
        return [r[0] for r in db.execute(f"SELECT id FROM story{cond} ORDER BY COALESCE(score, 0.0) DESC", args).fetchall()]
    ids = []
    for c, w in db.execute(f"SELECT DISTINCT country, window_days FROM story{cond}", args).fetchall():
        if n:
            ids += [r[0] for r in db.execute("SELECT id FROM story WHERE country=? AND window_days=? ORDER BY COALESCE(score, 0.0) DESC LIMIT ?", (c, w, n))]
        for (cat,) in db.execute("SELECT DISTINCT category FROM story WHERE country=? AND window_days=?", (c, w)).fetchall():
            ids += [r[0] for r in db.execute(
                "SELECT id FROM story WHERE country=? AND window_days=? AND category=? ORDER BY COALESCE(score, 0.0) DESC" + (f" LIMIT {per_category}" if per_category else ""), (c, w, cat))]
    return list(dict.fromkeys(ids))


def run(db):
    recent = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    has_country = "country" in {r[1] for r in db.execute("PRAGMA table_info(story)")}
    has_feed = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='feed'").fetchone())
    story_sql = "SELECT id, country FROM story" if has_country else "SELECT id, NULL AS country FROM story"
    row_sql = (
        "SELECT a.source_id, a.syndicated_of, COALESCE(a.published_at, a.fetched_at) t, "
        "s.name AS source_name, s.scope, s.kind, fs.scope AS feed_scope "
        "FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source s ON s.id=a.source_id "
        "LEFT JOIN feed f ON f.id=a.feed_id LEFT JOIN source fs ON fs.id=f.source_id "
        "WHERE sa.story_id=? AND COALESCE(sa.similarity, 1.0) >= 0.93"
        if has_feed else
        "SELECT a.source_id, a.syndicated_of, COALESCE(a.published_at, a.fetched_at) t, "
        "s.name AS source_name, s.scope, s.kind, NULL AS feed_scope "
        "FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source s ON s.id=a.source_id "
        "WHERE sa.story_id=? AND COALESCE(sa.similarity, 1.0) >= 0.93"
    )
    for sid, country in db.execute(story_sql).fetchall():
        rows = db.execute(row_sql, (sid,)).fetchall()
        independent = {r["source_id"] for r in rows if r["syndicated_of"] is None}
        scopes = {packs.resolve_scope(country, r["source_id"], r["source_name"], r["scope"], r["feed_scope"]) for r in rows}
        growing = sum(r["t"] >= recent for r in rows) / len(rows) >= 0.4
        n_indep = len(independent)
        consensus = (2.0 + 0.5 * (n_indep - 5)) if n_indep >= 5 else (1.0 if n_indep >= 3 else 0.0)
        coverage = (n_indep + consensus + 0.5 * (len(scopes) - 1) + (1.0 if growing else 0.0)
                    + 0.2 * math.log2(len(rows)))
        pol_row = db.execute("SELECT policy, themes FROM story WHERE id=?", (sid,)).fetchone()
        policy = 0.3 if (not pol_row or pol_row[0] is None) else pol_row[0]
        themes_str = (pol_row[1] or "").lower() if pol_row else ""
        is_election = any(w in themes_str for w in ("election", "választás", "bầu cử", "élection", "elección", "wahl", "wybory", "выборы", "seçim", "انتخابات"))
        # Standing rule 8: elections receive top policy priority and priority coverage boost
        score = coverage * (0.6 + 0.5 * policy) + 1.2 * policy + (2.5 if is_election else 0.0)
        db.execute("UPDATE story SET score=? WHERE id=?", (round(score, 2), sid))
    db.commit()
    print("rank: scored", db.execute("SELECT COUNT(*) FROM story").fetchone()[0], "stories")
