"""Stage 7: write the data files the website reads (site/data/*.json).

One file per country and time window. Only headlines, short verified excerpts and links are exported:
no full article text ever leaves the local database.
"""
import json
from datetime import datetime, timezone

from . import packs
from .config import ROOT
from .rank import dashboard_story_ids

SITE_DATA = ROOT / "site" / "data"
WINDOWS = {1: "24h", 7: "7d"}
CATEGORIES = ["internal_politics", "economics", "foreign_policy", "defence_security", "society", "other"]
MAX_ARTICLES_LISTED = 12


def _story(db, s):
    rows = db.execute(
        "SELECT a.id, a.title, a.url, a.language, a.published_at, a.syndicated_of, src.id AS source_id, src.name AS source, "
        "src.scope, src.kind FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source src ON src.id=a.source_id "
        "WHERE sa.story_id=? ORDER BY (a.syndicated_of IS NOT NULL), a.published_at", (s["id"],)).fetchall()
    independent = {r["source_id"] for r in rows if r["syndicated_of"] is None}
    by_scope = {sc: sum(r["scope"] == sc for r in rows) for sc in ("domestic", "abroad_local", "international")}
    rep = next(r for r in rows if r["id"] == s["representative_article_id"])
    excerpts = db.execute(
        "SELECT x.id, x.text, a.url, src.name AS source, src.scope FROM excerpt x JOIN article a ON a.id=x.article_id "
        "JOIN source src ON src.id=a.source_id WHERE x.story_id=? ORDER BY x.id", (s["id"],)).fetchall()
    return {
        "id": s["id"],
        "category": s["category"],
        "score": s["score"],
        "themes": json.loads(s["themes"] or "[]"),         # why it ranks where it does (themes.yaml)
        "headline": {"title": rep["title"], "url": rep["url"], "source": rep["source"], "language": rep["language"]},
        "first_seen": s["first_seen"],
        "last_seen": s["last_seen"],
        "articles": len(rows),
        "independent_sources": len(independent),
        "by_scope": by_scope,
        "evidence": "OFFICIAL" if any(r["kind"] == "official" for r in rows) else "REPORTED",
        "abroad_only": by_scope["domestic"] == 0 and (by_scope["abroad_local"] + by_scope["international"]) > 0,
        "excerpts": [{"text": x["text"], "source": x["source"], "scope": x["scope"], "url": x["url"]} for x in excerpts],
        "sources": [{"title": r["title"], "url": r["url"], "source": r["source"], "scope": r["scope"],
                     "language": r["language"], "published": r["published_at"], "copy": r["syndicated_of"] is not None}
                    for r in rows[:MAX_ARTICLES_LISTED]],
    }


def _write(name, payload, var):
    """Write <name>.json, and <name>.js which sets a global. The page loads the .js through a script tag,
    because browsers refuse to fetch() local files when the page is opened straight from a folder."""
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    (SITE_DATA / f"{name}.json").write_text(text, encoding="utf8")
    key = "" if var == "ARGOS_INDEX" else f'["{name}"]'
    head = f"window.{var} = {text};" if not key else f"window.{var} = window.{var} || {{}}; window.{var}{key} = {text};"
    (SITE_DATA / f"{name}.js").write_text(head + "\n", encoding="utf8")


def run(db):
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    countries = []
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        periods = []
        for days, label in WINDOWS.items():
            ids = dashboard_story_ids(db, cid, days)
            if not ids:
                continue
            stories = [_story(db, db.execute("SELECT * FROM story WHERE id=?", (i,)).fetchone()) for i in ids]
            stories.sort(key=lambda st: -st["score"])
            totals = {c: db.execute("SELECT COUNT(*) FROM story WHERE country=? AND window_days=? AND category=?", (cid, days, c)).fetchone()[0]
                      for c in CATEGORIES}          # all stories found in the window, of which the top ones are exported
            payload = {"country": cid, "period": label, "days": days, "generated_at": now, "categories": CATEGORIES,
                       "totals": totals, "stories": stories}
            _write(f"{cid}-{label}", payload, "ARGOS_DATA")
            periods.append({"id": label, "label": {"24h": "Last 24 hours", "7d": "Last 7 days"}[label], "file": f"{cid}-{label}.json"})
            print(f"export: {cid}-{label}.json with {len(stories)} stories")
        if periods:
            countries.append({"id": cid, "name": pack["name"], "language": pack["language"],
                              "abroad_label": pack["abroad_label"], "periods": periods})
    _write("index", {"generated_at": now, "countries": countries}, "ARGOS_INDEX")
