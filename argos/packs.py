"""Country packs (decision D15): everything specific to one country lives in countries/<id>/.
    pack.yaml     name, language, relevance words, excerpt cleanup, topic wording
    sources.yaml  outlets and feeds
    themes.yaml   the country's additions to the shared themes.yaml
"""
import re
from functools import lru_cache

import yaml

from .config import COUNTRIES_DIR, ROOT


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
    parts = [re.escape(w) for w in pack["mention"]] + list(pack.get("mention_regex") or [])
    pack["mention_re"] = re.compile("|".join(parts), re.I)
    sections = pack.get("url_sections") or {}
    pack["foreign_sections"] = {s.lower() for s in sections.get("foreign", [])}
    pack["skip_sections"] = {s.lower() for s in sections.get("skip", [])}
    ex = pack.get("excerpt") or {}
    pack["dateline_re"] = re.compile(ex["dateline"], re.I) if ex.get("dateline") else None
    pack["noise_re"] = re.compile(ex["noise"], re.I) if ex.get("noise") else None
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
            for k in ("label", "weight"):
                if k in t:
                    cur[k] = t[k]
        else:
            themes[t["id"]] = dict(t, keywords=list(t.get("keywords", [])), describe=list(t.get("describe", [])))
    return {"default_weight": base["default_weight"], "themes": list(themes.values())}


def url_section(url):
    """First part of an article address's path, lower case: 'https://telex.hu/kulfold/2026/..' -> 'kulfold'."""
    m = re.match(r"https?://[^/]+/([^/?#]+)", url or "")
    return m.group(1).lower() if m else ""
