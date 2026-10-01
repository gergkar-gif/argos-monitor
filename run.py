"""Run the pipeline. `python run.py` runs every stage; `python run.py extract` runs one
(ingest | extract | normalise | relevance | embed | cluster | classify | policy | rank | excerpts | verify | export | prune | report | top | sample)."""
import sys

from argos import classify, cluster, db as dbmod, embed, excerpts, export, extract, ingest, normalise, policy, prune, rank, relevance, translate


def report(db):
    print("\nArticles by scope (with full text / total):")
    q = ("SELECT s.scope, COUNT(*) total, SUM(a.text IS NOT NULL) txt "
         "FROM article a JOIN source s ON s.id=a.source_id GROUP BY 1")
    for r in db.execute(q):
        print(f"  {r['scope']:14} {r['txt']:5} / {r['total']}")
    print("Total articles:", db.execute("SELECT COUNT(*) FROM article").fetchone()[0])


def top(db, n=10, per_category=3):
    """Print the top stories overall and per category."""
    def line(r):
        arts = db.execute("SELECT s.scope, a.source_id, a.syndicated_of FROM story_article sa JOIN article a ON a.id=sa.article_id "
                          "JOIN source s ON s.id=a.source_id WHERE sa.story_id=?", (r["id"],)).fetchall()
        indep = len({a["source_id"] for a in arts if a["syndicated_of"] is None})
        by = {sc: sum(a["scope"] == sc for a in arts) for sc in ("domestic", "abroad_vi", "international")}
        title = db.execute("SELECT title FROM article WHERE id=?", (r["representative_article_id"],)).fetchone()[0]
        print(f"  {r['score']:5.1f}  {r['category'][:10]:10} {len(arts)} articles, {indep} independent "
              f"(dom {by['domestic']}, vi-abroad {by['abroad_vi']}, intl {by['international']})\n         {title[:120]}")
    print(f"== TOP {n} OVERALL")
    for r in db.execute("SELECT * FROM story ORDER BY score DESC LIMIT ?", (n,)):
        line(r)
    for cat, in db.execute("SELECT DISTINCT category FROM story ORDER BY 1"):
        c = db.execute("SELECT COUNT(*) FROM story WHERE category=?", (cat,)).fetchone()[0]
        print(f"\n== {cat} ({c} stories)")
        for r in db.execute("SELECT * FROM story WHERE category=? ORDER BY score DESC LIMIT ?", (cat, per_category)):
            line(r)


def sample(db, k=30):
    """Print stories for hand-checking: a random sample of stories with 2+ articles, plus the 5 biggest."""
    import random
    random.seed(1)
    def show(sid):
        rows = db.execute("SELECT s.scope, a.source_id, a.title FROM story_article sa JOIN article a ON a.id=sa.article_id "
                          "JOIN source s ON s.id=a.source_id WHERE sa.story_id=? ORDER BY a.published_at", (sid,)).fetchall()
        print(f"\n--- story {sid} ({len(rows)} articles)")
        for r in rows[:8]:
            print(f"   [{r['scope'][:3]}] {r['source_id']:13} {r['title'][:110]}")
        if len(rows) > 8:
            print(f"   ... +{len(rows) - 8} more")
    multi = [r[0] for r in db.execute("SELECT story_id FROM story_article GROUP BY 1 HAVING COUNT(*)>=2")]
    print("== 5 BIGGEST")
    for r in db.execute("SELECT story_id FROM story_article GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 5"):
        show(r[0])
    print("\n== RANDOM SAMPLE OF MULTI-ARTICLE STORIES")
    for sid in random.sample(multi, min(k, len(multi))):
        show(sid)


STAGES = {"ingest": ingest.run, "extract": extract.run, "normalise": normalise.run, "relevance": relevance.run,
          "embed": embed.run, "cluster": cluster.run, "classify": classify.run, "policy": policy.run, "rank": rank.run,
          "translate": translate.run, "excerpts": excerpts.run, "verify": excerpts.verify, "export": export.run, "prune": prune.run,
          "report": report, "top": top, "sample": sample}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    db = dbmod.connect()
    for name in sys.argv[1:] or ["ingest", "extract", "normalise", "relevance", "embed", "cluster", "classify", "policy", "rank", "excerpts", "verify", "export", "prune", "report"]:
        print(f"\n== {name}")
        STAGES[name](db)
