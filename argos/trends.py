"""Stage: what people search for right now, from Google Trends' public RSS feed, one list per country.

Sorted by search volume (highest first) and filtered to drop foreign sports scores, streaming spam,
and bare newspaper navigation searches (e.g. "dân trí", "bama.hu").
"""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write
from .textutil import clean

URL = "https://trends.google.com/trending/rss?geo={}"
# Foreign football/F1/US sports fixtures, betting tips, horoscopes, lotteries, gaming, and pirated stream spam.
NOISE_RE = re.compile(
    r"\b(vs\.?|đấu với|nhận định bóng đá|bóng đá|lịch thi đấu|tỷ số|kết quả bóng đá|ngoại hạng anh|cúp c1|"
    r"tử vi|con giáp|xổ số|kết quả xổ số|vietlott|dự báo thời tiết|horoscope|horoszkóp|zodiac|lottery|powerball|mega millions|"
    r"live free broadcast|en vivo|transmisiones|best bets|fantasy football|black friday|cyber monday|"
    r"premier league|serie a|la liga|bundesliga|champions league|europa league|mls|nfl|nba|nhl|mlb|ufc|atp|wta|ncaa|"
    r"f1|formula 1|nagydíj|grand prix|qualifying|standings|pole-ja|hat-trick|world champions|albo d'oro|"
    r"onefootball|fociclub|bongda|the race|yahoo sports|sky sports|espn|nemzeti sport|m4 sport|supersport|"
    r"soccer|football|basketball|tennis|cricket|boxing|бокс[её]р\w*|foci|labdarúgás|portero|partido|fútbol|goles|marcador|"
    r"calcio|partita|футбол|баскетбол|хоккей|теннис|матч|сборная|вратарь|счет|чемпионат|"
    r"steam|roblox|minecraft|genshin|fortnite|valorant|highlights|box score|lineup|starting xi|fc|cf|fk|nk)\b",
    re.I,
)
NOISE_DOMAINS = (
    "flashscore.", "sofascore.", "transfermarkt.", "espn.", "nba.com", "nfl.com", "mlb.com", "nhl.com",
    "goal.com", "bongdaplus.", "thethao247.", "nemzetisport.", "m4sport.", "championat.", "sports.ru",
    "marca.com", "as.com", "gazzetta.it", "lequipe.fr", "skysports.com", "onefootball.com",
)
DOMAIN_RE = re.compile(r"^[\w-]+(?:\.co)?\.(hu|vn|kh|za|th|mm|rs|pl|tr|br|ph|id|ge|az|et|kz|com|net|org)$", re.I)


def _traffic(s):
    m = re.match(r"(\d+(?:\.\d+)?)([KM]?)", (s or "").replace(",", ""))
    return int(float(m.group(1)) * {"": 1, "K": 1000, "M": 1_000_000}[m.group(2)]) if m else 0


def _keep(pack, outlets, item):
    term = item["term"].strip()
    url = item.get("url") or ""
    url_low = url.lower()
    blob = f"{term} {item.get('news') or ''} {item.get('source') or ''}"
    if term.lower() in outlets or DOMAIN_RE.match(term):
        return False   # navigational search for a news site itself ("dân trí", "bama.hu")
    if "data:video" in url_low or any(d in url_low for d in NOISE_DOMAINS) or NOISE_RE.search(blob):
        return False   # pirated stream redirect, sports portal, horoscope, or routine sports score
    if not item.get("news") and len(term.split()) < 2:
        return False   # bare single-word query with no news context
    secs = packs.url_sections(url)
    if (secs & pack["skip_sections"]) or (secs & {"sport", "sports", "f1", "bong-da", "the-thao", "entertainment", "celebrity", "sztarvilag"}):
        return False
    return True


def run(db=None):
    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        geo = pack.get("geo")
        status, body = fetch.get(URL.format(geo)) if geo else (0, b"")
        if status != 200:
            print(f"trends: {cid}: HTTP {status}, skipped")
            continue
        outlets = ({str(o).lower() for lst in pack.get("aggregator_outlets", {}).values() for o in lst}
                   | {str(s["name"]).lower() for s in pack["sources"]}
                   | {urlparse(s.get("homepage") or "").netloc.removeprefix("www.").split(".")[0].lower() for s in pack["sources"]})
        items = [{"term": clean(e.title), "traffic": e.get("ht_approx_traffic"), "news": clean(e.get("ht_news_item_title")) or None,
                  "url": e.get("ht_news_item_url"), "source": clean(e.get("ht_news_item_source")) or None}
                 for e in feedparser.parse(body).entries]
        kept = [x for x in items if _keep(pack, outlets, x)]
        kept.sort(key=lambda x: _traffic(x.get("traffic")), reverse=True)
        out[cid] = kept[:8]
        print(f"trends: {cid}: kept {len(out[cid])} of {len(items)} searches")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("trends", {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "countries": out}, "ARGOS_TRENDS")
