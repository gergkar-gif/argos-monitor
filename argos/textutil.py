import html
import re
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

VN = timezone(timedelta(hours=7))

# Common tracking / marketing query parameters stripped during URL canonicalization (Media Cloud lift)
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_eid", "_ga", "_gl", "ref", "ref_src",
    "vn_source", "vn_campaign", "vn_medium", "session_id", "at_custom1", "at_custom2"
}

# Rule 7: Zero emojis across the entire project (broadsheet aesthetic & data hygiene)
EMOJI_RE = re.compile(
    r"["
    r"\U0001F1E6-\U0001F1FF"  # Regional Indicator Symbols (country flags)
    r"\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    r"\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F680-\U0001F6FF"  # Transport & Map Symbols
    r"\U0001F700-\U0001F77F"  # Alchemical Symbols
    r"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    r"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    r"\U0001FA00-\U0001FA6F"  # Chess Symbols
    r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    r"\u2600-\u26FF"          # Misc Symbols (weather, warning, coffee, sports)
    r"\u2700-\u27BF"          # Dingbats (writing instruments, stars, checks)
    r"\uFE0E-\uFE0F"          # Variation selectors
    r"\u200D"                 # Zero-width joiner
    r"]+",
    flags=re.UNICODE,
)


def nfc(s):
    """Rule 3: NFC-normalise Vietnamese text as soon as it is ingested."""
    return unicodedata.normalize("NFC", s or "")


def strip_emoji(s):
    """Rule 7: Strip emojis from external text."""
    return EMOJI_RE.sub("", s) if s else ""


def clean(s):
    """Rule 3: NFC; Rule 7: strip emojis; decode entities, resolve styled characters, and collapse spaces."""
    if not isinstance(s, str):
        s = str(s or "")
    for _ in range(2):
        s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", re.sub(r"<[^>]+>", " ", s))).strip()


def clean_url(raw_url):
    """Normalize a URL: strip tracking/marketing query parameters, strip fragments,
    normalize lower-case scheme/hostname, and clean redundant path separators (Media Cloud lift)."""
    if not raw_url or not isinstance(raw_url, str):
        return ""
    try:
        p = urllib.parse.urlsplit(raw_url.strip())
        if not p.scheme or not p.netloc:
            return raw_url.strip()
        scheme = p.scheme.lower()
        netloc = p.netloc.lower()
        if p.query:
            qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
            filtered = [(k, v) for k, v in qs if k.lower() not in TRACKING_PARAMS]
            query = urllib.parse.urlencode(filtered)
        else:
            query = ""
        path = re.sub(r"/+", "/", p.path)
        return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return raw_url.strip()


def parse_date(entry):
    """ISO UTC string or None. Handles feedparser's parsed time, plus the 'M/D/YYYY h:mm:ss AM' format
    that Tuoi Tre and Bao Chinh phu use (Vietnam time), and ISO 8601 strings."""
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if st:
        try:
            return datetime(*st[:6], tzinfo=timezone.utc).isoformat(timespec="seconds")
        except (ValueError, TypeError):
            pass
    raw = entry.get("published") or entry.get("updated") or ""
    raw = raw.strip() if isinstance(raw, str) else ""
    if not raw:
        return None
    try:
        d = datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=VN)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        pass
    try:
        d = parsedate_to_datetime(re.sub(r",(?=\S)", ", ", raw))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        pass
    try:
        d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return None


_SPAM_DELIM_RE = re.compile(
    r"(!\+!|\$\#|【[^】]*(?:live|canl[ıi]|stream|tv|ma[cç]|izle|watch)[^】]*】|\[(?:match|live|stream|watch|tv)[^\]]*\])",
    re.I,
)
_STREAM_PHRASE_RE = re.compile(
    r"\b(?:live\s+stream|livestream|stream\s+tv\s+channel|tv\s+channel\b.*\b(?:live|match|stream)|"
    r"how\s+to\s+watch|watch\s+live|free\s+live\s+stream|canl[ıi]\s+izle|canl[ıi]\s+yay[ıi]n|"
    r"ne\s+zaman[,:\s]+saat\s+ka[cç]ta|hangi\s+kanalda|ver\s+en\s+vivo|"
    r"en\s+vivo\b.*\b(?:vs\.?|v\.?)\b|transmisi[oó]n\s+en\s+vivo|"
    r"prediction\s+and\s+betting\s+tips|betting\s+tips|betting\s+odds|"
    r"stats\s*&\s*head-to-head|head-to-head\b.*\b(?:uefa|nations\s+league|concacaf|fifa|world\s+cup|premier\s+league|la\s+liga|serie\s+a|bundesliga|champions\s+league|europa\s+league))\b",
    re.I,
)
_LEAGUE_FIXTURE_RE = re.compile(
    r"\b(?:uefa\s+nations\s+league|concacaf\s+nations\s+league|champions\s+league|europa\s+league|"
    r"premier\s+league|la\s+liga|serie\s+a|bundesliga|copa\s+am[eé]rica|echipa\s+național[ăa]|"
    r"лиг[еаи]\s+наций|обзор\s+матча|первая\s+лига|تصفيات\s+أمم\s+أفريقيا|بهدف\s+قاتل)\b",
    re.I,
)
_VS_MATCH_RE = re.compile(
    r"(?:\b(?:v|vs\.?)\s+[^\n,:;]{2,35}\s+(?:match\s+live|live\s+stream|prediction|betting|preview|highlights|stats)\b|"
    r"\bin\s+match\s+against\b|^\d+[-:]\d+[.\s]+.*\b(?:serie|liga|match|goal|gol|win|beat|defeat)\b)",
    re.I,
)
_SPORTS_OUTLETS = {
    "dailysports", "tudn", "espn", "onefootball", "goal", "flashscore", "sofascore",
    "sky sports", "beinsports", "bein sports", "marca", "as", "l'équipe", "l'equipe",
    "nemzeti sport", "m4 sport", "trt spor", "a spor", "fanatik", "fotomac", "fotomaç",
    "sportbox", "championat", "championat.com", "championat.ru", "sports.ru",
    "российский футбольный союз", "алтайский спорт", "хоккейный клуб «динамо» москва",
    "sport.ua", "ua-football",
}
_SPAM_HOST_OUTLETS = ("universitat de barcelona", "日本取引所グループ", "ub.edu", "jpx.co.jp")


def is_sports_stream_spam(title, outlet="", url=""):
    """Reject SEO live-stream spam, betting tips, and routine sports match broadcasts."""
    t = (title or "").strip()
    o = (outlet or "").strip().lower()
    u = (url or "").strip().lower()
    if o in _SPORTS_OUTLETS:
        return True
    if not t:
        return False
    if _SPAM_DELIM_RE.search(t) or _STREAM_PHRASE_RE.search(t) or _LEAGUE_FIXTURE_RE.search(t) or _VS_MATCH_RE.search(t):
        return True
    if any(h in o or h in u for h in _SPAM_HOST_OUTLETS) and re.search(r"\b(live|stream|match|canl[ıi]|izle|tv|vs\.?|v)\b", t, re.I):
        return True
    return False
