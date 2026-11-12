"""Standardize direct regional coverage and unique international queries for the 21 desks lacking international scope.
Conforms strictly to D15: unique URLs and unique source IDs per pack.
"""
from pathlib import Path
import urllib.parse
import yaml

ROOT = Path(__file__).resolve().parent.parent
COUNTRIES_DIR = ROOT / "countries"

TARGET_DESKS = {
    "australia": "Australia",
    "belarus": "Belarus",
    "canada": "Canada",
    "egypt": "Egypt",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "israel": "Israel",
    "italy": "Italy",
    "north_korea": "North Korea",
    "pakistan": "Pakistan",
    "qatar": "Qatar",
    "russia": "Russia",
    "saudi_arabia": "Saudi Arabia",
    "singapore": "Singapore",
    "spain": "Spain",
    "sweden": "Sweden",
    "united_arab_emirates": "United Arab Emirates",
    "united_kingdom": "United Kingdom",
    "united_states": "United States",
    "venezuela": "Venezuela",
}

def main():
    print(f"Applying unique international scope sources to {len(TARGET_DESKS)} deficit desks...")
    
    for desk_id, desk_name in TARGET_DESKS.items():
        src_path = COUNTRIES_DIR / desk_id / "sources.yaml"
        if not src_path.exists():
            print(f"Skipping {desk_id}: sources.yaml not found")
            continue
            
        with open(src_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        sources = data.get("sources", [])
        
        # Check if already has international scope
        has_intl = any(s.get("scope") == "international" for s in sources)
        if has_intl:
            print(f"Desk {desk_id} already has international source, skipping.")
            continue
            
        # Build country-specific search query
        # Quoting if multiple words
        q_name = f'"{desk_name}"' if " " in desk_name else desk_name
        query_text = f"({q_name}) (diplomacy OR government OR election OR economy OR foreign) when:3d"
        encoded_query = urllib.parse.quote(query_text)
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        new_source = {
            "id": f"gnews_{desk_id}_intl",
            "name": f"Google News ({desk_name} - International Press)",
            "homepage": "https://news.google.com",
            "language": "en",
            "scope": "international",
            "kind": "media",
            "governing_body": "n/a (aggregator)",
            "state_affiliated": False,
            "aggregator": "google_news",
            "notes": f"Aggregator stream tracking international English-language reporting on {desk_name}.",
            "feeds": [
                {
                    "url": feed_url,
                    "section": "International Coverage",
                    "category_hint": "foreign_policy",
                    "active": True
                }
            ]
        }
        
        sources.append(new_source)
        data["sources"] = sources
        
        with open(src_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            
        print(f"Added international aggregator for {desk_id}: gnews_{desk_id}_intl")

if __name__ == "__main__":
    main()
