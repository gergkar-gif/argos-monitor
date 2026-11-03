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
MERGE_SIMILARITY = 0.95    # shortcut: untuned guess, read the "closest pairs" lines in the run log and adjust
RELATED_SIMILARITY = 0.925 # below the merge level: shown on the site as related coverage
SIMILARITY = 0.92          # core cluster (>93% calibrated); 85-93% and 75-85% bands attach around the core centre
RAW_85 = 0.895             # e5-small raw cosine corresponding to 85% calibrated similarity
RAW_75 = 0.860             # e5-small raw cosine corresponding to 75% calibrated similarity
MAX_BROAD_PER_STORY = 6


def _calibrate(raw):
    """Map e5-small's compressed cosine cone (0.860-0.925+) onto human-readable 75-85%, 85-93%, >93% bands."""
    return np.interp(raw, [0.78, RAW_75, RAW_85, 0.925, 1.0], [0.0, 0.75, 0.85, 0.93, 1.0])


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
    core_labels = sorted(set(labels))
    centres, los, his, sizes, reps = {}, {}, {}, {}, {}
    for l in core_labels:
        m = np.where(labels == l)[0]
        c = X[m].mean(0); c /= np.linalg.norm(c)
        centres[l], los[l], his[l], sizes[l] = c, float(t[m].min()), float(t[m].max()), len(m)
        reps[l] = int(m[int(np.argmax(X[m] @ c))])

    # Absorb small (1-2 article) clusters whose centre sits in the 85-93% band of a larger story within MAX_GAP_DAYS.
    absorbed = {}
    for b in core_labels:
        if sizes[b] > 2:
            continue
        best_a, best_s = None, RAW_85
        for a in core_labels:
            if a == b or a in absorbed or (sizes[a], -a) <= (sizes[b], -b):
                continue
            if max(his[a], his[b]) - min(los[a], los[b]) > MAX_GAP_DAYS * 86400:
                continue
            s = float(centres[a] @ centres[b])
            if s >= best_s:
                best_a, best_s = a, s
        if best_a is not None:
            absorbed[b] = best_a

    active_labels = [l for l in core_labels if l not in absorbed]
    # Close/Broader bands only borrow single-article stories, each placed in its closest story only,
    # so an article never shows up inside two multi-article stories (live data had ~40% repeated rows).
    absorbers = set(absorbed.values())
    single = {l for l in active_labels if sizes[l] == 1 and l not in absorbers}
    loose = np.array([m for l in single for m in np.where(labels == l)[0]], dtype=int)
    best = {}   # article index -> (raw similarity, story label)
    sa_rows = []
    for l in active_labels:
        core_m = np.where(labels == l)[0]
        abs_m = [m for b, target in absorbed.items() if target == l for m in np.where(labels == b)[0]]
        all_85 = list(core_m) + abs_m
        times = sorted(datetime.fromtimestamp(t[m], timezone.utc).isoformat(timespec="seconds") for m in all_85)
        rep_idx = reps[l]
        cur = db.execute("INSERT INTO story (country,window_days,window_start,window_end,first_seen,last_seen,representative_article_id) "
                         "VALUES (?,?,?,?,?,?,?)", (country, days, cutoff, now.isoformat(timespec="seconds"), times[0], times[-1], rows[rep_idx]["id"]))
        sid = cur.lastrowid
        ids[l] = sid
        c = centres[l]
        for m in core_m:
            raw_s = 1.0 if m == rep_idx else max(float(X[m] @ c), float(X[m] @ X[rep_idx]))
            cal_s = 1.0 if m == rep_idx else max(0.93, round(float(_calibrate(raw_s)), 3))
            sa_rows.append((sid, rows[m]["id"], cal_s))
        for m in abs_m:
            raw_s = max(float(X[m] @ c), float(X[m] @ X[rep_idx]))
            cal_s = min(0.929, max(0.85, round(float(_calibrate(raw_s)), 3)))
            sa_rows.append((sid, rows[m]["id"], cal_s))
        # Candidate 85-93% (Close coverage) and 75-85% (Broader context) articles within MAX_GAP_DAYS.
        if l in single or not len(loose):
            continue
        sims = np.maximum(X[loose] @ c, X[loose] @ X[rep_idx])
        near_time = (np.maximum(his[l], t[loose]) - np.minimum(los[l], t[loose])) <= MAX_GAP_DAYS * 86400
        ok = near_time & (sims >= RAW_75) & (sims < 0.925)
        for m, s in zip(loose[ok], sims[ok]):
            if s > best.get(int(m), (0.0, None))[0]:
                best[int(m)] = (float(s), l)

    by_story = {}
    for m, (s, l) in best.items():
        by_story.setdefault(l, []).append((s, m))
    for l, cands in by_story.items():
        cands.sort(reverse=True)
        close_c = [(s, m) for s, m in cands if s >= RAW_85][:6]
        broad_c = [(s, m) for s, m in cands if s < RAW_85][:MAX_BROAD_PER_STORY]
        sa_rows += [(ids[l], rows[m]["id"], min(0.929, max(0.85, round(float(_calibrate(s)), 3)))) for s, m in close_c]
        sa_rows += [(ids[l], rows[m]["id"], min(0.849, max(0.75, round(float(_calibrate(s)), 3)))) for s, m in broad_c]

    db.executemany("INSERT OR REPLACE INTO story_article (story_id, article_id, similarity) VALUES (?,?,?)", sa_rows)
    rel_rows = [(ids[a], ids[b], s) for s, _, _, a, b in close if a in ids and b in ids]
    db.executemany("INSERT INTO story_related VALUES (?,?,?)", rel_rows + [(b, a, s) for a, b, s in rel_rows])
    db.commit()
    print(f"cluster {country} {days}d: {n} articles -> {len(active_labels)} stories ({len(absorbed)} absorbed in 85-93% band)")


def run(db, similarity=SIMILARITY):
    db.execute("DELETE FROM excerpt")
    db.execute("DELETE FROM story_related")
    db.execute("DELETE FROM story_article")
    db.execute("DELETE FROM story")
    for country in packs.pack_ids():
        for days in WINDOWS:
            _cluster_window(db, country, days, similarity)
