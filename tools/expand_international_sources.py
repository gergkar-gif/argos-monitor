"""Expand country desks with direct regional & international outlets (Audit Fix #7).
Adds 2-3 reputable international and regional news feeds tailored by region
to eliminate reliance solely on Google News aggregator queries.
"""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
COUNTRIES_DIR = ROOT / "countries"

INTL_TEMPLATES = {
    "bbc_europe": {
        "id": "bbc_news_europe",
        "name": "BBC News (Europe)",
        "homepage": "https://www.bbc.com/news/world/europe",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers Europe; only items explicitly referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "category_hint": "general"}],
    },
    "bbc_asia": {
        "id": "bbc_news_asia",
        "name": "BBC News (Asia)",
        "homepage": "https://www.bbc.com/news/world/asia",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers Asia; only items explicitly referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/asia/rss.xml", "category_hint": "general"}],
    },
    "bbc_me": {
        "id": "bbc_news_me",
        "name": "BBC News (Middle East)",
        "homepage": "https://www.bbc.com/news/world/middle_east",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers the Middle East; only items referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "category_hint": "general"}],
    },
    "bbc_africa": {
        "id": "bbc_news_africa",
        "name": "BBC News (Africa)",
        "homepage": "https://www.bbc.com/news/world/africa",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers Africa; only items referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "category_hint": "general"}],
    },
    "bbc_latam": {
        "id": "bbc_news_latam",
        "name": "BBC News (Latin America)",
        "homepage": "https://www.bbc.com/news/world/latin_america",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers Latin America; only items referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml", "category_hint": "general"}],
    },
    "bbc_us_canada": {
        "id": "bbc_news_us_canada",
        "name": "BBC News (US & Canada)",
        "homepage": "https://www.bbc.com/news/world/us_and_canada",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "BBC (British Broadcasting Corporation)",
        "state_affiliated": False,
        "notes": "Covers North America; only items referencing the country are ingested.",
        "feeds": [{"url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", "category_hint": "general"}],
    },
    "dw_world": {
        "id": "dw_english",
        "name": "Deutsche Welle (English)",
        "homepage": "https://www.dw.com",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "Deutsche Welle (German public statutory international broadcaster)",
        "state_affiliated": True,
        "notes": "Global broadcast feed; filtered strictly by country mention words.",
        "feeds": [{"url": "https://rss.dw.com/rdf/rss-en-all", "category_hint": "general"}],
    },
    "france24_en": {
        "id": "france24_english",
        "name": "France 24 (English)",
        "homepage": "https://www.france24.com/en",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "France Médias Monde",
        "state_affiliated": True,
        "notes": "International coverage; filtered strictly by country mention words.",
        "feeds": [{"url": "https://www.france24.com/en/rss", "category_hint": "general"}],
    },
    "aljazeera_en": {
        "id": "aljazeera_english",
        "name": "Al Jazeera English",
        "homepage": "https://www.aljazeera.com",
        "language": "en",
        "scope": "international",
        "kind": "media",
        "governing_body": "Al Jazeera Media Network",
        "state_affiliated": True,
        "notes": "Global Middle Eastern & developing world coverage; filtered by country mention words.",
        "feeds": [{"url": "https://www.aljazeera.com/xml/rss/all.xml", "category_hint": "general"}],
    },
}

REGION_MAPPING = {
    "Western Europe": ["bbc_europe", "dw_world", "france24_en"],
    "Eastern Europe": ["bbc_europe", "dw_world", "france24_en"],
    "Central & Southeast Europe": ["bbc_europe", "dw_world", "france24_en"],
    "Mediterranean": ["bbc_me", "aljazeera_en", "france24_en"],
    "Middle East": ["bbc_me", "aljazeera_en", "france24_en"],
    "Sub-Saharan Africa": ["bbc_africa", "france24_en", "aljazeera_en"],
    "South America": ["bbc_latam", "france24_en", "aljazeera_en"],
    "Central America": ["bbc_latam", "france24_en", "aljazeera_en"],
    "Caribbean": ["bbc_latam", "france24_en", "aljazeera_en"],
    "East Asia": ["bbc_asia", "dw_world", "aljazeera_en"],
    "Southeast Asia": ["bbc_asia", "dw_world", "aljazeera_en"],
    "South Asia": ["bbc_asia", "dw_world", "aljazeera_en"],
    "Central Asia": ["bbc_asia", "dw_world", "aljazeera_en"],
    "South Caucasus": ["bbc_asia", "dw_world", "aljazeera_en"],
    "Oceania": ["bbc_asia", "dw_world", "aljazeera_en"],
    "North America": ["bbc_us_canada", "dw_world", "france24_en"],
}

def expand_desk(country_dir):
    pack_path = country_dir / "pack.yaml"
    src_path = country_dir / "sources.yaml"
    if not (pack_path.exists() and src_path.exists()):
        return 0

    pack = yaml.safe_load(pack_path.read_text(encoding="utf-8")) or {}
    region = pack.get("region", "Western Europe")
    template_keys = REGION_MAPPING.get(region, ["bbc_europe", "dw_world", "france24_en"])

    src_data = yaml.safe_load(src_path.read_text(encoding="utf-8")) or {}
    sources = src_data.get("sources", [])
    existing_ids = {s.get("id") for s in sources}
    existing_urls = {f.get("url") for s in sources for f in s.get("feeds", [])}

    added = 0
    for key in template_keys:
        tpl = INTL_TEMPLATES[key]
        # Avoid duplicate ids or duplicate urls
        tpl_id = tpl["id"]
        tpl_url = tpl["feeds"][0]["url"]
        if tpl_id in existing_ids or tpl_url in existing_urls:
            continue
        # Also avoid adding UK-specific BBC to UK domestic desk if already covered domestically
        if country_dir.name in ("united_kingdom",) and "bbc" in tpl_id:
            continue
        if country_dir.name in ("germany",) and "dw" in tpl_id:
            continue
        if country_dir.name in ("france",) and "france24" in tpl_id:
            continue
        if country_dir.name in ("qatar",) and "aljazeera" in tpl_id:
            continue

        sources.append(dict(tpl))
        existing_ids.add(tpl_id)
        existing_urls.add(tpl_url)
        added += 1

    if added > 0:
        src_data["sources"] = sources
        src_path.write_text(yaml.dump(src_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return added

def main():
    total_added = 0
    desks_updated = 0
    for d in sorted(COUNTRIES_DIR.iterdir()):
        if d.is_dir() and (d / "sources.yaml").exists():
            count = expand_desk(d)
            if count > 0:
                total_added += count
                desks_updated += 1

    print(f"Expanded international coverage: added {total_added} direct international sources across {desks_updated} desks.")

if __name__ == "__main__":
    main()
