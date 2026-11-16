"""Cloud go/no-go test. Run from a cloud machine (the GitHub 'Cloud probe' workflow) to see which news sites
refuse it. Fetches every active feed, then a sample of article pages, then GDELT and the model host.
Prints a table; it never fails the job, because the result is the information."""
import collections
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import feedparser
import trafilatura
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.config import DATA_DIR, ROOT   # noqa: E402
from argos.fetch import get               # noqa: E402

DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
PAGES_PER_OUTLET = 1
MAX_SAMPLE_OUTLETS = 60

sources = [s for d in sorted((ROOT / "countries").iterdir()) if (d / "sources.yaml").exists()
           for s in yaml.safe_load((d / "sources.yaml").read_text(encoding="utf8"))["sources"]]
print(f"Running on: {os.environ.get('RUNNER_OS', 'unknown')} | data dir {DATA_DIR}\n")

print("== FEEDS")
feed_tasks = [(s["id"], f["url"]) for s in sources for f in s.get("feeds", []) if f.get("active", True)]


def _probe_feed(task):
    sid, url = task
    try:
        code, body = get(url)
        parsed = feedparser.parse(body) if code == 200 else None
        entries = getattr(parsed, "entries", None) or []
        links = [e.link for e in entries[:PAGES_PER_OUTLET] if e.get("link")]
        return sid, url, code, len(entries), links
    except Exception:
        return sid, url, 0, 0, []


feed_bad, sample = 0, collections.defaultdict(list)
with ThreadPoolExecutor(max_workers=20) as pool:
    for sid, url, code, n, links in pool.map(_probe_feed, feed_tasks):
        ok = n > 0
        feed_bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {sid:15} HTTP {code} items {n:4}  {url}")
        if ok and len(sample) < MAX_SAMPLE_OUTLETS and len(sample[sid]) < PAGES_PER_OUTLET:
            sample[sid] += links[:PAGES_PER_OUTLET - len(sample[sid])]
print(f"\nfeeds failing: {feed_bad}")

print("\n== ARTICLE PAGES (sample per outlet)")
page_tasks = [(sid, u) for sid, urls in list(sample.items())[:MAX_SAMPLE_OUTLETS] for u in urls[:PAGES_PER_OUTLET]]


def _probe_page(task):
    sid, u = task
    try:
        code, body = get(u)
        text = trafilatura.extract(body) if code == 200 else None
        good = bool(text and len(text) > 200)
        return sid, code, good
    except Exception:
        return sid, 0, False


page_ok = page_bad = 0
by_sid = collections.defaultdict(list)
with ThreadPoolExecutor(max_workers=16) as pool:
    for sid, code, good in pool.map(_probe_page, page_tasks):
        by_sid[sid].append(f"{code}{'+text' if good else ''}")
        page_ok += good
        page_bad += not good
for sid, results in by_sid.items():
    print(f"{sid:15} {' '.join(results)}")
print(f"\npages with usable text: {page_ok}, without: {page_bad}")

print("\n== GDELT")
code, body = get("https://api.gdeltproject.org/api/v2/doc/doc?query=vietnam%20sourcelang:eng&mode=artlist&format=json&maxrecords=5&timespan=1d", timeout=60)
print(f"HTTP {code}; {'articles returned' if b'articles' in body[:200] else body[:120]!r}")

print("\n== MODEL HOST")
code, _ = get("https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/tokenizer.json", timeout=60)
print(f"Hugging Face tokenizer: HTTP {code}")
