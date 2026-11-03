"""Self-check for textutil: NFC normalisation (Rule 3) and emoji stripping (Rule 7).
Run: python tests/test_textutil.py"""
import sys
import pathlib
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos.textutil import clean, nfc, strip_emoji

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

print("ok textutil tests passed")
