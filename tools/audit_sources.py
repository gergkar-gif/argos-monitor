"""Audit country source registries to verify source depth and independence standards (Phase 3).
Rule: Each country pack should have at least 10 independent direct sources (excluding aggregators).
Usage: python tools/audit_sources.py [--min 10] [--fail-under]"""
import argparse
import os
import pathlib
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def audit_sources(min_required=10):
    countries_dir = ROOT / "countries"
    packs = sorted([d for d in countries_dir.iterdir() if (d / "sources.yaml").exists()])
    report = []

    for d in packs:
        cid = d.name
        with open(d / "sources.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        sources = data.get("sources", [])
        direct = [s for s in sources if s.get("kind") != "aggregator" and not s.get("aggregator")]
        aggregators = [s for s in sources if s.get("kind") == "aggregator" or s.get("aggregator")]
        report.append({
            "country": cid,
            "total": len(sources),
            "direct": len(direct),
            "aggregators": len(aggregators),
            "compliant": len(direct) >= min_required
        })

    compliant_count = sum(1 for r in report if r["compliant"])
    total_count = len(report)

    print(f"Argos Monitor Source Registry Audit")
    print(f"Total packs: {total_count} | Compliant (>= {min_required} direct): {compliant_count} | Deficit: {total_count - compliant_count}\n")
    print(f"{'Country Pack':<25} {'Direct':<8} {'Aggregators':<12} {'Total':<8} {'Status'}")
    print("-" * 65)

    for r in report:
        status = "PASS" if r["compliant"] else "DEFICIT"
        print(f"{r['country']:<25} {r['direct']:<8} {r['aggregators']:<12} {r['total']:<8} {status}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit independent source depth across country packs.")
    parser.add_argument("--min", type=int, default=10, help="Minimum direct sources required (default: 10)")
    parser.add_argument("--fail-under", action="store_true", help="Exit with code 1 if any country is under minimum")
    args = parser.parse_args()

    results = audit_sources(min_required=args.min)
    if args.fail_under and any(not r["compliant"] for r in results):
        sys.exit(1)
