import html
import re
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone

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
    s = s or ""
    for _ in range(2):
        s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = EMOJI_RE.sub("", s)
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", re.sub(r"<[^>]+>", " ", s))).strip()


def clean_url(raw_url):
    """Normalize a URL: strip tracking/marketing query parameters, strip fragments,
    normalize lower-case scheme/hostname, and clean redundant path separators (Media Cloud lift)."""
    if not raw_url:
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
    that Tuoi Tre and Bao Chinh phu use (Vietnam time)."""
    if entry.get("published_parsed"):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat(timespec="seconds")
    raw = (entry.get("published") or entry.get("updated") or "").strip()
    try:
        d = datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=VN)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        return None
