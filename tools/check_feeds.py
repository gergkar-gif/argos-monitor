"""Roadmap step 1 check: fetch every active feed in every country pack's sources.yaml; OK = valid feed with at least one item."""
import sys, pathlib, concurrent.futures as cf, yaml
from probe import probe
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(__file__).resolve().parent.parent
sources = [s for d in sorted((root / "countries").iterdir()) if (d / "sources.yaml").exists()
           for s in yaml.safe_load((d / "sources.yaml").read_text(encoding="utf8"))["sources"]]
jobs = [(s["id"], f["url"]) for s in sources for f in s.get("feeds", []) if f.get("active", True)]
with cf.ThreadPoolExecutor(6) as ex:
    results = list(ex.map(lambda j: probe(j[1])[1], jobs))
bad = 0
for (sid, url), res in zip(jobs, results):
    ok = "feed items=" in res and "items=0" not in res
    bad += not ok
    print(("OK   " if ok else "FAIL "), sid, url, "|", res)
print(f"\n{len(jobs) - bad}/{len(jobs)} feeds OK")
sys.exit(1 if bad else 0)
