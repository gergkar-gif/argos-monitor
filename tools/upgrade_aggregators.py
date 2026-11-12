"""Add native-language Google News aggregator feeds to country packs lacking local-language coverage."""
import yaml
from pathlib import Path
from argos.config import COUNTRIES_DIR

CONFIGS = {
    # MENA (Arabic)
    "egypt": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D9%85%D8%B5%D8%B1+OR+%D8%A7%D9%84%D8%B3%D9%8A%D8%B3%D9%8A+OR+%D8%A7%D9%84%D8%AD%D9%83%D9%88%D9%85%D8%A9+%D8%A7%D9%84%D9%85%D8%B5%D8%B1%D9%8A%D8%A9+when:2d&hl=ar&gl=EG&ceid=EG:ar",
    },
    "saudi_arabia": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%D8%A9+OR+%D8%A7%D9%84%D8%B1%D9%8A%D8%A7%D8%B6+OR+%D9%88%D9%84%D9%8A+%D8%A7%D9%84%D8%B9%D9%87%D8%AF+when:2d&hl=ar&gl=SA&ceid=SA:ar",
    },
    "united_arab_emirates": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D8%A7%D9%84%D8%A5%D9%85%D8%A7%D8%B1%D8%A7%D8%AA+OR+%D8%A3%D8%A8%D9%88%D8%B8%D8%A8%D9%8A+OR+%D8%AF%D8%A8%D9%8A+when:2d&hl=ar&gl=AE&ceid=AE:ar",
    },
    "qatar": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D9%82%D8%B7%D8%B1+OR+%D8%A7%D9%84%D8%AF%D9%88%D8%AD%D8%A9+OR+%D8%A3%D9%85%D9%8A%D8%B1+%D9%82%D8%B7%D8%B1+when:2d&hl=ar&gl=QA&ceid=QA:ar",
    },
    "iraq": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82+OR+%D8%A8%D8%BA%D8%AF%D8%A7%D8%AF+OR+%D8%A7%D9%84%D8%AD%D9%83%D9%88%D9%85%D8%A9+%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82%D9%8A%D8%A9+when:2d&hl=ar&gl=IQ&ceid=IQ:ar",
    },
    "syria": {
        "lang": "ar",
        "name": "Arabic",
        "url": "https://news.google.com/rss/search?q=%D8%B3%D9%88%D8%B1%D9%8A%D8%A7+OR+%D8%AF%D9%85%D8%B4%D9%82+when:2d&hl=ar&gl=SY&ceid=SY:ar",
    },
    # Francophone
    "morocco": {
        "lang": "fr",
        "name": "French",
        "url": "https://news.google.com/rss/search?q=Maroc+OR+gouvernement+OR+Rabat+when:2d&hl=fr&gl=MA&ceid=MA:fr",
    },
    "belgium": {
        "lang": "fr",
        "name": "French",
        "url": "https://news.google.com/rss/search?q=Belgique+OR+Bruxelles+OR+gouvernement+when:2d&hl=fr&gl=BE&ceid=BE:fr",
    },
    # Hispanophone
    "chile": {
        "lang": "es",
        "name": "Spanish",
        "url": "https://news.google.com/rss/search?q=Chile+OR+Santiago+OR+Gobierno+when:2d&hl=es-419&gl=CL&ceid=CL:es-419",
    },
    "peru": {
        "lang": "es",
        "name": "Spanish",
        "url": "https://news.google.com/rss/search?q=Per%C3%BA+OR+Lima+OR+Gobierno+when:2d&hl=es-419&gl=PE&ceid=PE:es-419",
    },
    "ecuador": {
        "lang": "es",
        "name": "Spanish",
        "url": "https://news.google.com/rss/search?q=Ecuador+OR+Quito+OR+Gobierno+when:2d&hl=es-419&gl=EC&ceid=EC:es-419",
    },
    "central_america": {
        "lang": "es",
        "name": "Spanish",
        "url": "https://news.google.com/rss/search?q=Centroam%C3%A9rica+OR+SICA+OR+Guatemala+OR+Honduras+OR+%22El+Salvador%22+when:2d&hl=es-419&gl=GT&ceid=GT:es-419",
    },
    # Lusophone
    "brazil": {
        "lang": "pt",
        "name": "Portuguese",
        "url": "https://news.google.com/rss/search?q=Brasil+OR+Bras%C3%ADlia+OR+governo+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    },
    "portugal": {
        "lang": "pt",
        "name": "Portuguese",
        "url": "https://news.google.com/rss/search?q=Portugal+OR+Lisboa+OR+governo+when:2d&hl=pt-PT&gl=PT&ceid=PT:pt-150",
    },
    # Germanic & Nordic
    "austria": {
        "lang": "de",
        "name": "German",
        "url": "https://news.google.com/rss/search?q=%C3%96sterreich+OR+Wien+OR+Bundesregierung+when:2d&hl=de&gl=AT&ceid=AT:de",
    },
    "switzerland": {
        "lang": "de",
        "name": "German",
        "url": "https://news.google.com/rss/search?q=Schweiz+OR+Bundesrat+OR+Bern+when:2d&hl=de-CH&gl=CH&ceid=CH:de",
    },
    "netherlands": {
        "lang": "nl",
        "name": "Dutch",
        "url": "https://news.google.com/rss/search?q=Nederland+OR+kabinet+OR+Den+Haag+when:2d&hl=nl&gl=NL&ceid=NL:nl",
    },
    "norway": {
        "lang": "no",
        "name": "Norwegian",
        "url": "https://news.google.com/rss/search?q=Norge+OR+regjeringen+OR+Stortinget+when:2d&hl=no&gl=NO&ceid=NO:no",
    },
    "denmark": {
        "lang": "da",
        "name": "Danish",
        "url": "https://news.google.com/rss/search?q=Danmark+OR+regeringen+OR+Folketinget+when:2d&hl=da&gl=DK&ceid=DK:da",
    },
    # Eastern Europe & Mediterranean
    "russia": {
        "lang": "ru",
        "name": "Russian",
        "url": "https://news.google.com/rss/search?q=%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F+OR+%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0+OR+%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D1%81%D1%82%D0%B2%D0%BE+when:2d&hl=ru&gl=RU&ceid=RU:ru",
    },
    "belarus": {
        "lang": "be",
        "name": "Belarusian/Russian",
        "url": "https://news.google.com/rss/search?q=%D0%91%D0%B5%D0%BB%D0%B0%D1%80%D1%83%D1%81%D1%8C+OR+%D0%9C%D0%B8%D0%BD%D1%81%D0%BA+when:2d&hl=ru&gl=BY&ceid=BY:ru",
    },
    "turkey": {
        "lang": "tr",
        "name": "Turkish",
        "url": "https://news.google.com/rss/search?q=T%C3%BCrkiye+OR+Ankara+OR+h%C3%BCk%C3%BCmet+when:2d&hl=tr&gl=TR&ceid=TR:tr",
    },
    "greece": {
        "lang": "el",
        "name": "Greek",
        "url": "https://news.google.com/rss/search?q=%CE%95%CE%BB%CE%BB%CE%AC%CE%B4%CE%B1+OR+%CE%BA%CF%85%CE%B2%CE%AD%CF%81%CE%BD%CE%B7%CF%83%CE%B7+OR+%CE%91%CE%B8%CE%AE%CE%BD%CE%B1+when:2d&hl=el&gl=GR&ceid=GR:el",
    },
    "romania": {
        "lang": "ro",
        "name": "Romanian",
        "url": "https://news.google.com/rss/search?q=Rom%C3%A2nia+OR+Bucure%C8%99ti+OR+Guvern+when:2d&hl=ro&gl=RO&ceid=RO:ro",
    },
    "israel": {
        "lang": "he",
        "name": "Hebrew",
        "url": "https://news.google.com/rss/search?q=%D7%99%D7%A9%D7%A8%D7%90%D7%9C+OR+%D7%94%D7%9E%D7%9E%D7%A9%D7%9C%D7%94+OR+%D7%99%D7%A8%D7%95%D7%A9%D7%9C%D7%99%D7%9D+when:2d&hl=he&gl=IL&ceid=IL:he",
    },
    # Asia
    "china": {
        "lang": "zh",
        "name": "Chinese",
        "url": "https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD+OR+%E5%8C%97%E4%BA%AC+OR+%E5%9B%BD%E5%8A%A1%E9%99%A2+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    },
    "vietnam": {
        "lang": "vi",
        "name": "Vietnamese",
        "url": "https://news.google.com/rss/search?q=%22Vi%E1%BB%87t+Nam%22+OR+%22Ch%C3%ADnh+ph%E1%BB%A7%22+OR+%22Th%E1%BB%A7+t%C6%B0%E1%BB%9Bng%22+when:2d&hl=vi&gl=VN&ceid=VN:vi",
    },
    "malaysia": {
        "lang": "ms",
        "name": "Malay",
        "url": "https://news.google.com/rss/search?q=Malaysia+OR+%22Kuala+Lumpur%22+OR+kerajaan+when:2d&hl=ms&gl=MY&ceid=MY:ms",
    },
    "pakistan": {
        "lang": "ur",
        "name": "Urdu",
        "url": "https://news.google.com/rss/search?q=%D9%BE%D8%A7%DA%A9%D8%B3%D8%AA%D8%A7%D9%86+OR+%D8%AD%DA%A9%D9%88%D9%85%D8%AA+when:2d&hl=ur&gl=PK&ceid=PK:ur",
    },
    "north_korea": {
        "lang": "ko",
        "name": "Korean",
        "url": "https://news.google.com/rss/search?q=%EB%B6%81%ED%95%9C+OR+%ED%8F%89%EC%96%91+OR+%EA%B9%80%EC%A0%95%EC%9D%80+when:2d&hl=ko&gl=KR&ceid=KR:ko",
    },
    "armenia": {
        "lang": "hy",
        "name": "Armenian",
        "url": "https://news.google.com/rss/search?q=%D5%80%D5%A1%D5%85%D5%A1%D5%BD%D5%8F%D5%A1%D5%B6+OR+%D4%B5%D6%80%D6%87%D5%A1%D5%B6+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
    "azerbaijan": {
        "lang": "az",
        "name": "Azerbaijani",
        "url": "https://news.google.com/rss/search?q=Az%C9%99rbaycan+OR+Bak%C4%B1+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
    "georgia": {
        "lang": "ka",
        "name": "Georgian",
        "url": "https://news.google.com/rss/search?q=%E1%83%A1%E1%83%90%E1%83%A5%E1%83%90%E1%83%A0%E1%83%97%E1%83%95%E1%83%94%E1%83%9A%E1%83%9D+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
    "cambodia": {
        "lang": "km",
        "name": "Khmer",
        "url": "https://news.google.com/rss/search?q=%E1%9E%80%E1%9E%98%E1%9F%92%E1%9E%96%E1%9E%BB%E1%9E%87%E1%9E%B6+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
    "laos": {
        "lang": "lo",
        "name": "Lao",
        "url": "https://news.google.com/rss/search?q=%E0%BA%A5%E0%BA%B2%E0%BA%A7+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
    "myanmar": {
        "lang": "my",
        "name": "Burmese",
        "url": "https://news.google.com/rss/search?q=%E1%80%99%E1%80%BC%E1%80%94%E1%80%BA%E1%80%99%E1%80%AC+when:2d&hl=en-US&gl=US&ceid=US:en",
    },
}

def run():
    upgraded = 0
    for cid, conf in CONFIGS.items():
        src_path = COUNTRIES_DIR / cid / "sources.yaml"
        if not src_path.exists():
            continue
        data = yaml.safe_load(src_path.read_text(encoding="utf8")) or {}
        sources = data.get("sources", [])
        
        # Check if already present
        sid = f"gnews_{cid}_{conf['lang']}"
        existing_ids = {s.get("id") for s in sources}
        if sid in existing_ids:
            continue
        
        # Check if URL already exists
        existing_urls = {f["url"] for s in sources for f in s.get("feeds", []) if "url" in f}
        if conf["url"] in existing_urls:
            continue

        c_name = cid.replace("_", " ").title()
        new_source = {
            "id": sid,
            "name": f"Google News ({c_name} National News - {conf['name']})",
            "homepage": "https://news.google.com",
            "language": conf["lang"],
            "scope": "domestic",
            "kind": "media",
            "governing_body": "Google LLC",
            "state_affiliated": False,
            "aggregator": "google_news",
            "feeds": [
                {
                    "url": conf["url"],
                    "section": f"National News ({conf['name']})",
                    "category_hint": "internal_politics",
                }
            ],
        }
        sources.append(new_source)
        data["sources"] = sources
        
        # Save back cleanly
        src_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False, width=120), encoding="utf8")
        upgraded += 1
        print(f"Upgraded {cid} with {sid}")
        
    print(f"\nDone: {upgraded} country packs upgraded.")

if __name__ == "__main__":
    run()
