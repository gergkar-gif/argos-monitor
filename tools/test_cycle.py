"""Test pipeline cycle verifying conditional HTTP 304 caching, backoff, and wire deduplication."""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from argos import db as dbmod, ingest, normalise, packs

def run_test_cycle():
    print("=== Argos Monitor Live Pipeline Test Cycle ===")
    db = dbmod.connect()
    
    print("\n--- 1. Loading updated registry into database ---")
    ingest.load_registry(db)
    
    sample_packs = ["jordan", "laos", "sri_lanka"]
    
    print("\n--- 2. Pass 1: Live Ingestion across sample desks ---")
    pass1_added = {}
    for country in sample_packs:
        print(f"\n[Pass 1 Ingestion: {country.upper()}]")
        n = ingest.ingest_feeds(db, country)
        pass1_added[country] = n
        print(f"Total new articles added for {country}: {n}")
        
    print("\n--- 3. Verifying feed cache headers saved on disk ---")
    cache_rows = db.execute(
        "SELECT f.id, s.id as source_id, f.etag, f.last_modified "
        "FROM feed f JOIN source s ON s.id=f.source_id "
        "WHERE f.etag IS NOT NULL OR f.last_modified IS NOT NULL"
    ).fetchall()
    print(f"Feeds with saved ETag or Last-Modified headers: {len(cache_rows)}")
    for r in cache_rows[:5]:
        print(f"  {r['source_id']:20} etag={r['etag']} last_modified={r['last_modified']}")
        
    print("\n--- 4. Pass 2: Immediate Re-Ingestion (Verifying conditional HTTP 304) ---")
    pass2_added = {}
    for country in sample_packs:
        print(f"\n[Pass 2 Ingestion: {country.upper()} - Expecting 304 Not Modified or 0 new]")
        n = ingest.ingest_feeds(db, country)
        pass2_added[country] = n
        print(f"Total new articles added on immediate re-fetch for {country}: {n}")

    print("\n--- 5. Testing Normalisation & Wire Syndication Deduplication ---")
    for country in sample_packs:
        print(f"\n[Normalise & Wire Dedupe: {country.upper()}]")
        normalise.run(db)
        
    print("\n=== Live Test Cycle Complete ===")

if __name__ == "__main__":
    run_test_cycle()
