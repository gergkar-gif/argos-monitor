"""Stage 4b: group articles into stories, once per country and time window (7 days and 24 hours).
Average-linkage agglomerative clustering on cosine distance, where articles published more than
MAX_GAP_DAYS apart can never be joined (an event has a time footprint)."""
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from . import packs
from .embed import DIM

WINDOWS = (7, 1)     # days
MAX_GAP_DAYS = 3
MERGE_SIMILARITY = 0.96    # shortcut: untuned guess, read the "closest pairs" lines in the run log and adjust
RELATED_SIMILARITY = 0.93  # below the merge level: shown on the site as related coverage
SIMILARITY = 0.92    # cosine; e5 scores are compressed (unrelated pairs ~0.85). Hand-checked 0.90-0.94 on 2026-09-30.


def _time(row):
    return datetime.fromisoformat(row["published_at"] or row["fetched_at"]).timestamp()


def _merge(X, t, labels):
    """Second pass: join stories whose centres are very close (average linkage splits big events whose headlines vary).
    Returns the new labels, the merges done and the remaining close pairs, as (similarity, label, label) with the first
    article index of each side. Greedy, with the centre recomputed after every merge."""
    ks = sorted(set(labels))
    lab = np.searchsorted(ks, labels)
    k = len(ks)
    sums = np.zeros((k, X.shape[1]))
    np.add.at(sums, lab, X)
    lo, hi = np.full(k, np.inf), np.full(k, -np.inf)
    np.minimum.at(lo, lab, t)
    np.maximum.at(hi, lab, t)
    first = np.full(k, len(lab))
    np.minimum.at(first, lab, np.arange(len(lab)))
    unit = sums / np.linalg.norm(sums, axis=1, keepdims=True)
    S = unit @ unit.T
    far = np.maximum(hi[:, None], hi[None, :]) - np.minimum(lo[:, None], lo[None, :]) > MAX_GAP_DAYS * 86400   # merged span stays short, so daily bulletins do not chain into one story
    S[far] = -1.0
    np.fill_diagonal(S, -1.0)
    merges = []
    while k > 1:
        i, j = np.unravel_index(np.argmax(S), S.shape)
        if S[i, j] < MERGE_SIMILARITY:
            break
        merges.append((float(S[i, j]), int(first[i]), int(first[j]), int((lab == i).sum()), int((lab == j).sum())))
        sums[i] += sums[j]; lo[i] = min(lo[i], lo[j]); hi[i] = max(hi[i], hi[j]); first[i] = min(first[i], first[j])
        lab[lab == j] = i
        unit[i] = sums[i] / np.linalg.norm(sums[i])
        S[j, :] = S[:, j] = -1.0
        far_i = np.maximum(hi, hi[i]) - np.minimum(lo, lo[i]) > MAX_GAP_DAYS * 86400
        row = unit @ unit[i]
        row[far_i] = -1.0
        row[~np.isin(np.arange(k), lab)] = -1.0
        row[i] = -1.0
        S[i, :] = S[:, i] = row
    close = [(float(S[a, b]), int(first[a]), int(first[b]), a, b) for a, b in zip(*np.where(np.triu(S) >= RELATED_SIMILARITY))]
    return lab, merges, sorted(close, reverse=True)


def _title(db, rows, idx):
    return db.execute("SELECT title FROM article WHERE id=?", (rows[idx]["id"],)).fetchone()[0][:90]


def _cluster_window(db, country, days, similarity):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat(timespec="seconds")
    rows = db.execute("SELECT a.id, a.published_at, a.fetched_at, e.vec FROM article a JOIN embedding e ON e.article_id=a.id "
                      "WHERE a.relevant=1 AND a.country=? AND COALESCE(a.published_at, a.fetched_at) >= ? ORDER BY a.id",
                      (country, cutoff)).fetchall()
    n = len(rows)
    if n == 0:
        print(f"cluster {country} {days}d: no articles")
        return
    X = np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(n, DIM)
    t = np.array([_time(r) for r in rows])
    D = 1.0 - X @ X.T
    D[np.abs(t[:, None] - t[None, :]) > MAX_GAP_DAYS * 86400] = 2.0
    np.fill_diagonal(D, 0.0)
    labels = AgglomerativeClustering(n_clusters=None, metric="precomputed", linkage="average",
                                     distance_threshold=1.0 - similarity).fit_predict(D.astype(np.float64))
    del D
    labels, merges, close = _merge(X, t, labels)
    for sim, a, b, na, nb in merges[:10]:
        print(f"  merged {sim:.3f} ({na}+{nb} articles): {_title(db, rows, a)} | {_title(db, rows, b)}")
    for sim, a, b, _, _ in close[:10]:
        print(f"  closest pair kept apart {sim:.3f}: {_title(db, rows, a)} | {_title(db, rows, b)}")
    print(f"  merge pass: {len(merges)} merges, {len(close)} related pairs")
    ids = {}
    for label in sorted(set(labels)):
        members = np.where(labels == label)[0]
        centre = X[members].mean(0)          # representative = the article closest to the cluster centre
        rep = rows[members[int(np.argmax(X[members] @ centre))]]["id"]
        times = sorted(datetime.fromtimestamp(t[m], timezone.utc).isoformat(timespec="seconds") for m in members)
        cur = db.execute("INSERT INTO story (country,window_days,window_start,window_end,first_seen,last_seen,representative_article_id) "
                         "VALUES (?,?,?,?,?,?,?)", (country, days, cutoff, now.isoformat(timespec="seconds"), times[0], times[-1], rep))
        ids[label] = cur.lastrowid
    db.executemany("INSERT INTO story_article VALUES (?,?)", [(ids[l], r["id"]) for l, r in zip(labels, rows)])
    db.executemany("INSERT INTO story_related VALUES (?,?,?)",
                   [(ids[a], ids[b], s) for s, _, _, a, b in close] + [(ids[b], ids[a], s) for s, _, _, a, b in close])
    db.commit()
    sizes = np.bincount(labels)
    sizes = sizes[sizes > 0]
    print(f"cluster {country} {days}d: {n} articles -> {len(sizes)} stories; {int((sizes == 1).sum())} single-article, "
          f"{int((sizes >= 3).sum())} with 3+ articles, largest {sizes.max()}")


def run(db, similarity=SIMILARITY):
    db.execute("DELETE FROM excerpt")
    db.execute("DELETE FROM story_related")
    db.execute("DELETE FROM story_article")
    db.execute("DELETE FROM story")
    for country in packs.pack_ids():
        for days in WINDOWS:
            _cluster_window(db, country, days, similarity)
