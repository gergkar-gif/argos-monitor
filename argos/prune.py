"""Housekeeping: drop articles older than RETAIN_DAYS so the database stays small (it is kept between cloud runs)."""
from datetime import datetime, timedelta, timezone

RETAIN_DAYS = 45


def run(db):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETAIN_DAYS)).isoformat(timespec="seconds")
    old = "SELECT id FROM article WHERE COALESCE(published_at, fetched_at) < ?"
    db.execute(f"DELETE FROM embedding WHERE article_id IN ({old})", (cutoff,))
    db.execute(f"DELETE FROM translation WHERE article_id IN ({old})", (cutoff,))
    n = db.execute("DELETE FROM article WHERE COALESCE(published_at, fetched_at) < ?", (cutoff,)).rowcount
    db.commit()
    db.execute("VACUUM")
    print(f"prune: removed {n} articles older than {RETAIN_DAYS} days")
