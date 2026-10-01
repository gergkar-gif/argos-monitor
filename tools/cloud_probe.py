"""Cloud go/no-go test. Run from a cloud machine (the GitHub 'Cloud probe' workflow) to see which news sites
refuse it. Fetches every active feed, then a few article pages per outlet, then GDELT and the model host.
Prints a table; it never fails the job, because the result is the information."""
import collections
import os
import pathlib
import sys
from urllib.parse import urlparse

import feedparser
import trafilatura
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.config import DATA_DIR, ROOT   # noqa: E402
from argos.fetch import get               # noqa: E402

DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
PAGES_PER_OUTLET = 3

sources = [s for d in sorted((ROOT / "countries").iterdir()) if (d / "sources.yaml").exists()
           for s in yaml.safe_load((d / "sources.yaml").read_text(encoding="utf8"))["sources"]]
print(f"Running on: {os.environ.get('RUNNER_OS', 'unknown')} | data dir {DATA_DIR}\n")

print("== FEEDS")
feed_bad, sample = 0, collections.defaultdict(list)
for s in sources:
    for f in s.get("feeds", []):
        if not f.get("active", True):
            continue
        code, body = get(f["url"])
        parsed = feedparser.parse(body) if code == 200 else None
        n = len(parsed.entries) if parsed else 0
        ok = n > 0
        feed_bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {s['id']:15} HTTP {code} items {n:4}  {f['url']}")
        if ok and len(sample[s["id"]]) < PAGES_PER_OUTLET:
            sample[s["id"]] += [e.link for e in parsed.entries[:PAGES_PER_OUTLET] if e.get("link")]
print(f"\nfeeds failing: {feed_bad}")

print("\n== ARTICLE PAGES (first few per outlet)")
page_ok = page_bad = 0
for sid, urls in sample.items():
    results = []
    for u in urls[:PAGES_PER_OUTLET]:
        code, body = get(u)
        text = trafilatura.extract(body) if code == 200 else None
        good = bool(text and len(text) > 200)
        results.append(f"{code}{'+text' if good else ''}")
        page_ok += good
        page_bad += not good
    print(f"{sid:15} {' '.join(results)}")
print(f"\npages with usable text: {page_ok}, without: {page_bad}")

print("\n== GDELT")
code, body = get("https://api.gdeltproject.org/api/v2/doc/doc?query=vietnam%20sourcelang:eng&mode=artlist&format=json&maxrecords=5&timespan=1d", timeout=60)
print(f"HTTP {code}; {'articles returned' if b'articles' in body[:200] else body[:120]!r}")

print("\n== MODEL HOST")
code, _ = get("https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/tokenizer.json", timeout=60)
print(f"Hugging Face tokenizer: HTTP {code}")
