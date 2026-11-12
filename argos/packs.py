"""Country packs (decision D15): everything specific to one country lives in countries/<id>/.
    pack.yaml     name, language, relevance words, excerpt cleanup, topic wording
    sources.yaml  outlets and feeds
    themes.yaml   the country's additions to the shared themes.yaml
"""
import re
import unicodedata
from functools import lru_cache
from urllib.parse import urlparse

import yaml

from .config import COUNTRIES_DIR, ROOT


def _term_regex(term):
    """Anchor term with word boundaries for spaced scripts, avoiding substring false positives."""
    escaped = re.escape(term)
    if any(any(unicodedata.name(ch, "").startswith(p) for p in ("CJK", "HIRAGANA", "KATAKANA", "THAI", "KHMER", "LAO", "HANGUL")) for ch in term):
        return escaped
    prefix = r"\b" if re.match(r"^\w", term, re.UNICODE) else ""
    suffix = r"\b" if re.match(r".*\w$", term, re.UNICODE) else ""
    return f"{prefix}{escaped}{suffix}"


def _read(path):
    return yaml.safe_load(path.read_text(encoding="utf8")) or {}


def pack_ids():
    return sorted(p.name for p in COUNTRIES_DIR.iterdir() if (p / "pack.yaml").exists())


@lru_cache(maxsize=None)
def load(country):
    d = COUNTRIES_DIR / country
    pack = _read(d / "pack.yaml")
    pack["sources"] = _read(d / "sources.yaml")["sources"]
    for src in pack["sources"]:
        src["id"] = str(src["id"])      # an id like 444 is read by YAML as a number
    parts = [_term_regex(w) for w in pack.get("mention", [])] + list(pack.get("mention_regex") or [])
    pack["mention_re"] = re.compile("|".join(parts), re.I)
    sections = pack.get("url_sections") or {}
    skip = sections.get("skip") or pack.get("skip_sections") or []
    pack["foreign_sections"] = {s.lower() for s in sections.get("foreign", [])}
    pack["skip_sections"] = {s.lower() for s in skip}
    ex = pack.get("excerpt") or {}
    dateline = ex.get("dateline") or pack.get("dateline")
    pack["dateline_re"] = re.compile(dateline, re.I) if dateline else None
    noise = ex.get("noise") or pack.get("noise")
    pack["noise_re"] = re.compile(noise, re.I) if noise else None
    if "reddit" not in pack and "subreddits" in pack:
        pack["reddit"] = pack["subreddits"]
    pack["themes"] = merged_themes(d)
    return pack


def merged_themes(country_dir):
    """The shared themes plus the country's additions: same id extends (keywords and descriptions are added,
    label and weight may be overridden), a new id adds a theme."""
    base = _read(ROOT / "themes.yaml")
    themes = {t["id"]: dict(t, keywords=list(t.get("keywords", [])), describe=list(t.get("describe", []))) for t in base["themes"]}
    extra = country_dir / "themes.yaml"
    for t in (_read(extra).get("themes", []) if extra.exists() else []):
        if t["id"] in themes:
            cur = themes[t["id"]]
            cur["keywords"] += t.get("keywords", [])
            cur["describe"] += t.get("describe", [])
            for k in ("label", "weight", "category"):
                if k in t:
                    cur[k] = t[k]
        else:
            themes[t["id"]] = dict(t, keywords=list(t.get("keywords", [])), describe=list(t.get("describe", [])))
    return {"default_weight": base["default_weight"], "themes": list(themes.values())}


def url_section(url):
    """First part of an article address's path, lower case: 'https://telex.hu/kulfold/2026/..' -> 'kulfold'."""
    m = re.match(r"https?://[^/]+/([^/?#]+)", url or "")
    return m.group(1).lower() if m else ""


def url_sections(url):
    """All path parts of an article address, lower case: 'https://pravda.sk/spravy/svet/clanok/..' -> {'spravy', 'svet', 'clanok'}."""
    path = urlparse(url or "").path.lower()
    return {p for p in path.strip("/").split("/") if p}
