"""Stage 4b: group articles into stories, once per time window (7 days and 24 hours).
Average-linkage agglomerative clustering on cosine distance, where articles published more than
MAX_GAP_DAYS apart can never be joined (an event has a time footprint)."""
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .embed import DIM

WINDOWS = (7, 1)     # days
MAX_GAP_DAYS = 3
SIMILARITY = 0.92    # cosine; e5 scores are compressed (unrelated pairs ~0.85). Hand-checked 0.90-0.94 on 2026-09-30.


def _time(row):
    return datetime.fromisoformat(row["published_at"] or row["fetched_at"]).timestamp()


def _cluster_window(db, days, similarity):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat(timespec="seconds")
    rows = db.execute("SELECT a.id, a.published_at, a.fetched_at, e.vec FROM article a JOIN embedding e ON e.article_id=a.id "
                      "WHERE a.vn_relevant=1 AND COALESCE(a.published_at, a.fetched_at) >= ? ORDER BY a.id", (cutoff,)).fetchall()
    n = len(rows)
    if n == 0:
        print(f"cluster: no articles in the last {days} day(s)")
        return
    X = np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(n, DIM)
    t = np.array([_time(r) for r in rows])
    D = 1.0 - X @ X.T
    D[np.abs(t[:, None] - t[None, :]) > MAX_GAP_DAYS * 86400] = 2.0
    np.fill_diagonal(D, 0.0)
    labels = AgglomerativeClustering(n_clusters=None, metric="precomputed", linkage="average",
                                     distance_threshold=1.0 - similarity).fit_predict(D.astype(np.float64))
    del D
    ids = {}
    for label in sorted(set(labels)):
        members = np.where(labels == label)[0]
        centre = X[members].mean(0)          # representative = the article closest to the cluster centre
        rep = rows[members[int(np.argmax(X[members] @ centre))]]["id"]
        times = sorted(datetime.fromtimestamp(t[m], timezone.utc).isoformat(timespec="seconds") for m in members)
        cur = db.execute("INSERT INTO story (window_days,window_start,window_end,first_seen,last_seen,representative_article_id) "
                         "VALUES (?,?,?,?,?,?)", (days, cutoff, now.isoformat(timespec="seconds"), times[0], times[-1], rep))
        ids[label] = cur.lastrowid
    db.executemany("INSERT INTO story_article VALUES (?,?)", [(ids[l], r["id"]) for l, r in zip(labels, rows)])
    db.commit()
    sizes = np.bincount(labels)
    print(f"cluster {days}d: {n} articles -> {len(sizes)} stories; {int((sizes == 1).sum())} single-article, "
          f"{int((sizes >= 3).sum())} with 3+ articles, largest {sizes.max()}")


def run(db, similarity=SIMILARITY):
    db.execute("DELETE FROM excerpt")
    db.execute("DELETE FROM story_article")
    db.execute("DELETE FROM story")
    for days in WINDOWS:
        _cluster_window(db, days, similarity)
