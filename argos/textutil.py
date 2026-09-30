import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))


def nfc(s):
    """Rule 3: NFC-normalise Vietnamese text as soon as it is ingested."""
    return unicodedata.normalize("NFC", s or "")


def clean(s):
    """Strip tags, decode HTML entities (feeds sometimes double-encode: &amp;apos;), NFC, collapse spaces."""
    s = s or ""
    for _ in range(2):
        s = html.unescape(s)
    return re.sub(r"\s+", " ", nfc(re.sub(r"<[^>]+>", " ", s))).strip()


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
