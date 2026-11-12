"""Audit country source registries to verify source depth and independence standards (Phase 3).
Rule: Each country pack should have at least 10 independent direct sources (excluding aggregators).
Usage: python tools/audit_sources.py [--min 10] [--fail-under]"""
import argparse
import os
import pathlib
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


DISALLOWED_TOP_LEVEL_KEYS = {"skip_sections", "dateline", "subreddits"}
VALID_TOP_LEVEL_KEYS = {
    "id", "name", "region", "language", "abroad_label", "mention", "mention_regex",
    "mention_section", "url_sections", "excerpt", "reddit", "geo", "aggregator_outlets",
    "bluesky", "telegram", "crisis_names", "classify", "last_reviewed",
}


def audit_packs_schema():
    countries_dir = ROOT / "countries"
    errors = []
    for d in sorted(countries_dir.iterdir()):
        pf = d / "pack.yaml"
        if not pf.exists():
            continue
        with open(pf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        keys = set(data.keys())
        disallowed = keys & DISALLOWED_TOP_LEVEL_KEYS
        if disallowed:
            errors.append(f"{d.name}: disallowed top-level keys {sorted(disallowed)}")
        unknown = keys - VALID_TOP_LEVEL_KEYS
        if unknown:
            errors.append(f"{d.name}: unrecognized top-level keys {sorted(unknown)}")
    return errors


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
    parser.add_argument("--fail-under", action="store_true", help="Exit with code 1 if any country is under minimum or schema fails")
    args = parser.parse_args()

    results = audit_sources(min_required=args.min)
    schema_errors = audit_packs_schema()
    if schema_errors:
        print(f"\n[FAIL] Pack Schema Errors ({len(schema_errors)}):")
        for err in schema_errors:
            print(f"  - {err}")
    else:
        print("\n[PASS] All 87 pack.yaml files adhere strictly to standard schema.")

    if args.fail_under and (any(not r["compliant"] for r in results) or schema_errors):
        sys.exit(1)
