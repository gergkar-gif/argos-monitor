"""Self-check for the merge pass: two clusters about one event join, an unrelated one and a far-in-time one do not.
Run: python tests/test_cluster_merge.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from argos.cluster import _merge

rng = np.random.default_rng(0)
unit = lambda v: v / np.linalg.norm(v, axis=-1, keepdims=True)
base, other = unit(rng.normal(size=(2, 384)).astype(np.float32))
near = lambda c, n: unit(c + 0.01 * rng.normal(size=(n, 384)).astype(np.float32))
X = np.vstack([near(base, 5), near(base, 5), near(other, 5), near(base, 5)])
day = 86400
t = np.concatenate([np.zeros(5), np.ones(5) * day, np.zeros(5), np.ones(5) * 30 * day])   # last group is the same event 30 days later
labels, merges, _ = _merge(X, t, np.repeat([0, 1, 2, 3], 5))
assert labels[0] == labels[5], "same event, close in time: must merge"
assert labels[0] != labels[10], "different event: must stay apart"
assert labels[0] != labels[15], "same wording 30 days later: must stay apart"
print("ok", len(merges), "merge")
