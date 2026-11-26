"""Self-check for textutil: NFC normalisation (Rule 3) and emoji stripping (Rule 7).
Run: python tests/test_textutil.py"""
import sys
import pathlib
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.textutil import clean, clean_url, is_routine_filler, is_sports_stream_spam, nfc, strip_emoji

# Rule 7: Zero emojis
s1 = "Breaking: \U0001f525 Alert in H\u00e0 N\u1ed9i \U0001f1fb\U0001f1f3 - Flood warning \u26a0\ufe0f in Budapest (\u00e1rv\u00edz)"
cleaned = clean(s1)
assert "\U0001f525" not in cleaned, "Fire emoji must be removed"
assert "\U0001f1fb" not in cleaned, "Flag emoji must be removed"
assert "\u26a0" not in cleaned, "Warning emoji must be removed"
assert "H\u00e0 N\u1ed9i" in cleaned, "Vietnamese text preserved"
assert "\u00e1rv\u00edz" in cleaned, "Hungarian text preserved"

# Styled math characters from social headlines must resolve to standard text
styled = "\U0001d5d8\U0001d5e7\U0001d5db\U0001d5dc\U0001d5e2\U0001d5e3\U0001d5dc\U0001d5d4"
assert clean(styled) == "ETHIOPIA", "Styled alphanumeric characters must resolve to standard text"

# Rule 3: NFC normalisation
decomposed = "Ha\u0300 No\u0302\u0323i"
assert clean(decomposed) == unicodedata.normalize("NFC", "H\u00e0 N\u1ed9i"), "Decomposed diacritics must normalise to NFC"

# Multiple spaces and html entities
s2 = "Tu\u1ed5i Tr\u1ebb &amp;amp; Thanh Ni\u00ean   reported  &lt;b&gt;live&lt;/b&gt;"
assert clean(s2) == "Tu\u1ed5i Tr\u1ebb & Thanh Ni\u00ean reported live"

# URL canonicalization (Media Cloud lift)
dirty_url = "HTTPS://VnExpress.NET//thoi-su/tin-moi.html?utm_source=facebook&utm_campaign=breaking&fbclid=XYZ123#comments"
expected_url = "https://vnexpress.net/thoi-su/tin-moi.html"
assert clean_url(dirty_url) == expected_url, f"URL must be canonicalized and tracking query params stripped: got {clean_url(dirty_url)}"

content_url = "https://news.example.com/article?id=9876&utm_medium=rss"
assert clean_url(content_url) == "https://news.example.com/article?id=9876", "Non-tracking query params must be retained"

# Central European sports outlets and live-ticker spam must be filtered
for outlet in ("kicker", "sport.pl", "sport.cz", "laola1"):
    assert is_sports_stream_spam("Match preview", outlet=outlet), f"Sports outlet {outlet} must be filtered"
for title in ("Bayern gegen BVB im Live-Ticker", "Polska - Niemcy transmisja na żywo", "Sparta vs Slavia přímý přenos"):
    assert is_sports_stream_spam(title), f"Live stream spam '{title}' must be filtered"
assert not is_sports_stream_spam("Bundestag verabschiedet Haushalt für das kommende Jahr", outlet="Tagesschau (ARD)")

# Routine daily weather forecasts and horoscopes must be filtered, while severe weather / disaster alerts stay
for title in (
    "Parashikimi i motit, 25 nëntor 2026",
    "Parashikimi i motit/ Si do variojnë temperaturat përgjatë ditës",
    "Weather forecast, November 25, 2026",
    "Weather Forecast For Sunday November 15",
    "Dự báo thời tiết 15/11/2026: Miền Bắc lại nắng mạnh, Hà Nội tăng lên 30 độ",
    "Прогноз погоды в Кыргызстане на 15 ноября: в Бишкеке без осадков",
    "Horoskopi 19 nëntor 2026, zbuloni parashikimet e yjeve",
):
    assert is_routine_filler(title), f"Routine filler '{title}' must be filtered"

for title in (
    "Nesër reshje intensive shiu në vend, IGJEO paralajmëron rrezik për përmbytje në 7 qarqe!",
    "Moti i keq/ Disa fshatra në Fan të Mirditës 5 ditë pa drita",
    "Weather forecast: Flood warning issued across northern provinces",
    "Parashikimi i motit: Stuhi e fortë dhe rrezik për përmbytje në Shkodër",
):
    assert not is_routine_filler(title), f"Severe weather / disaster news '{title}' must be kept"

print("ok textutil tests passed")
