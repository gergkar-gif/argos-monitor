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
    overrides = {}
    for sc, names in (pack.get("aggregator_outlets") or {}).items():
        for n in (names or []):
            overrides[str(n).lower().strip()] = sc
    pack["outlet_overrides"] = overrides
    pack["outlet_patterns"] = [
        (re.compile(r"\b" + re.escape(pat) + r"\b"), sc)
        for pat, sc in overrides.items()
        if len(pat) >= 4
    ]
    pack["themes"] = merged_themes(d)
    return pack


def resolve_scope(country, source_id, source_name, source_scope, feed_scope=None):
    """Resolve the reporting scope of a source for a specific country desk.
    Catalogued direct sources belong to one country only and use their own source_scope.
    Google News ('gn:*') sources are shared across desks, so their scope is resolved against
    the target country's aggregator_outlets rules first, falling back to feed_scope or 'international'."""
    sid = str(source_id or "")
    if not sid.startswith("gn:"):
        return source_scope or "domestic"
    if not country or not (COUNTRIES_DIR / country / "pack.yaml").exists():
        return feed_scope or source_scope or "international"
    pack = load(country)
    overrides = pack["outlet_overrides"]
    nl = str(source_name or "").lower().strip()
    if nl in overrides:
        return overrides[nl]
    cl = re.split(r"\s+[|\-–—·]\s+|\s*\(", nl)[0].strip()
    cl = re.sub(r"^(the|báo)\s+", "", cl).strip()
    if cl in overrides:
        return overrides[cl]
    for reg, sc in pack["outlet_patterns"]:
        if reg.search(nl) or reg.search(cl):
            return sc
    if feed_scope in ("domestic", "abroad_local", "international"):
        return feed_scope
    return "international"


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
