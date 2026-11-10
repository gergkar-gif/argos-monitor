"""Stage: crisis, conflict and official alerts per country, from free official sensors, conflict monitors,
GDELT 2.0 real-time CAMEO event streams, and optional ACLED API.
Only each feed's or source article's own verbatim title, summary, link and date are kept: no sentences of our own."""
import csv
import html
import io
import json
import os
import re
import urllib.parse
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write
from .textutil import clean

GDACS = "https://www.gdacs.org/xml/rss.xml"
USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.atom"
EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=14&limit=80"
US = "https://travel.state.gov/_res/rss/TAsTWs.xml"
UK = "https://www.gov.uk/foreign-travel-advice/{}.atom"
CRISISGROUP = "https://www.crisisgroup.org/rss"
UN_PEACE = "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml"
HRW = "https://www.hrw.org/rss/news"
LWJ = "https://www.longwarjournal.org/feed"
MSF = "https://www.msf.org/rss/all"
GDELT_BASE = "http://data.gdeltproject.org/gdeltv2/{}.export.CSV.zip"
ACLED_API = "https://api.acleddata.com/acled/read"
RECENT_DAYS = 7

REGIONAL_COUNTRIES = {
    "east_africa": ["sudan", "south sudan", "somalia", "eritrea", "uganda", "rwanda", "tanzania", "burundi", "djibouti", "darfur", "khartoum", "mogadishu"],
    "west_africa": ["mali", "burkina faso", "niger", "senegal", "ghana", "ivory coast", "côte d'ivoire", "cote d'ivoire", "guinea", "sierra leone", "liberia", "benin", "togo", "sahel", "bamako", "ouagadougou", "niamey"],
    "caribbean": ["haiti", "jamaica", "trinidad", "tobago", "bahamas", "cuba", "dominican republic", "barbados", "guyana", "suriname", "port-au-prince"],
    "central_america": ["guatemala", "el salvador", "honduras", "nicaragua", "costa rica", "panama", "belize"],
    "baltics": ["estonia", "latvia", "lithuania"],
    "pacific_islands": ["fiji", "papua new guinea", "solomon islands", "vanuatu", "samoa", "tonga"],
    "israel": ["gaza", "west bank", "hebron", "rafah", "jenin", "nablus", "palestinian", "palestine"],
    "lebanon": ["hezbollah", "beirut", "litani", "tyre", "sidon", "bekaa"],
    "saudi_arabia": ["yemen", "houthi", "houthis", "sanaa", "hodeidah", "hudaydah", "taiz", "aden", "marib"],
}

UK_SLUGS = {
    "dr_congo": "democratic-republic-of-the-congo",
    "united_states": "usa",
    "united_kingdom": None,
    "east_africa": "sudan",
    "west_africa": "mali",
    "caribbean": "haiti",
    "central_america": "guatemala",
    "baltics": "estonia",
    "pacific_islands": "papua-new-guinea",
}

ARMED_CONFLICT_RE = re.compile(
    r"\b(airstrike|airstrikes|air-strike|drone-strike|drone-attacks|drone-attack|missile|shelling|shelled|mortar|artillery|"
    r"bombing|bombed|suicide-bomb|car-bomb|ied|ambush|ambushed|insurgent|insurgents|insurgency|militant|militants|militia|militias|"
    r"rebel|rebels|terror|terrorist|terrorism|jihadist|isis|iswap|boko-haram|al-shabaab|houthi|houthis|hezbollah|hamas|taliban|rsf|idf|"
    r"troops|soldiers|military|army|forces|clash|clashes|clashed|gunmen|kidnap|kidnapped|abduct|abducted|hostage|hostages|massacre|"
    r"civilian-killings|civilians-killed|riot|riots|protesters|crackdown|tear-gas|curfew|martial-law|coup|sectarian|synagogue|mosque|church|temple)\b",
    re.I,
)
VIOLENCE_IMPACT_RE = re.compile(
    r"\b(attack|attacks|clash|clashes|ambush|strike|strikes|bomb|bombing|bombed|explosion|blast|shoot|shooting|shot|gunmen|"
    r"kill|killed|killing|dead|deaths|fatalities|casualties|massacre|kidnap|kidnapped|abduct|abducted|hostage|riot|riots|"
    r"raid|raided|shelling|shelled|wounded|injured|crackdown|arson)\b",
    re.I,
)
EXCLUDE_RE = re.compile(
    r"\b(festival|dance|theatre|theater|concert|music|album|song|singer|film|movie|championship|tournament|league|match|coach|"
    r"player|stadium|actor|actress|ranking|rankings|washroom|stock|market|shares|box-office|cricket|football|soccer|basketball|"
    r"baseball|golf|tennis|car-crash|road-accident|house-collapse|wife|husband|boyfriend|girlfriend|divorce|faces-court|judge-rejects|bail)\b",
    re.I,
)
CAMEO_LABELS = {
    "20": "Mass Violence",
    "19": "Armed Clash & Strike",
    "18": "Assault, Bombing & Kidnapping",
    "17": "Coercion & Crackdown",
    "14": "Violent Unrest & Riot",
}


def _eonet():
    status, body = fetch.get(EONET)
    if status != 200:
        return []
    try:
        return json.loads(body.decode("utf-8", errors="replace")).get("events") or []
    except ValueError:
        return []


def _feed(url):
    status, body = fetch.get(url)
    if status != 200:
        print(f"crisis: {url} -> HTTP {status}, skipped")
        return []
    return feedparser.parse(body.decode("utf-8", errors="replace")).entries


def _when(e):
    raw = (e.get("published") or e.get("updated") or "").strip()
    if raw:
        for fmt in ("%A, %B %d, %Y - %H:%M", "%a, %d %b %Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        try:
            d = parsedate_to_datetime(raw) if "," in raw else datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    st = e.get("published_parsed") or e.get("updated_parsed")
    if st:
        try:
            return datetime(*st[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def _summary(kind, e):
    raw = clean(html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary") or "")))
    raw = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s+", " ", raw)).strip()
    if kind == "US travel advisory":
        for s in re.split(r"(?<=\.)\s+", raw):
            if "due to" in s.lower() or "precaution" in s.lower():
                return s
    return raw.split(". ")[0] + ("." if raw and not raw.split(". ")[0].endswith(".") else "") if raw else ""


def _item(kind, e, level=None):
    d = _when(e)
    title = clean(re.sub(r"\s+", " ", e.title).strip())
    summary = _summary(kind, e)
    # UK atom feeds set every title to "<Country> travel advice" and put the actual change note in <summary>.
    if kind == "UK travel advice" and summary:
        title, summary = summary, ""
    return {"kind": kind, "title": title, "summary": summary, "url": e.link, "level": level,
            "date": d.isoformat(timespec="seconds") if d else None}


def _extract_html_title(url):
    status, body = fetch.get(url)
    if status != 200 or not body:
        return None
    head = body[:32768].decode("utf-8", errors="replace")
    m = (
        re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', head, re.I)
        or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', head, re.I)
        or re.search(r"<title[^>]*>([^<]+)</title>", head, re.I)
    )
    if not m:
        return None
    t = clean(html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()))
    # Strip trailing site-name suffixes (" - Al Jazeera", " | The Manila Times") if headline remains >= 25 chars
    for sep in (" | ", " - ", " — ", " – "):
        if sep in t:
            left = t.rsplit(sep, 1)[0].strip()
            if len(left) >= 25:
                t = left
                break
    return t if len(t) >= 20 else None


def _gdelt_events(now, db=None):
    """Fetch recent 15-minute GDELT 2.0 event intervals, filter for high-confidence kinetic violence/unrest,
    and verify each event's verbatim source headline (Rule 1)."""
    candidates = {}
    for mins in range(15, 135, 15):
        t = now - timedelta(minutes=mins)
        ts = t.strftime("%Y%m%d%H") + f"{(t.minute // 15) * 15:02d}00"
        status, zbytes = fetch.get(GDELT_BASE.format(ts))
        if status != 200 or not zbytes:
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
                content = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
                for r in csv.reader(io.StringIO(content), delimiter="\t"):
                    if len(r) <= 60:
                        continue
                    root, base = r[28], r[27]
                    if root not in ("18", "19", "20") and base not in ("145", "175"):
                        continue
                    loc, u = (r[52] or "").strip(), (r[60] or "").strip()
                    if not loc or not u.startswith(("http://", "https://")) or u in candidates:
                        continue
                    if ARMED_CONFLICT_RE.search(u) and VIOLENCE_IMPACT_RE.search(u) and not EXCLUDE_RE.search(u):
                        dt_iso = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
                        candidates[u] = (root, loc, dt_iso)
        except (zipfile.BadZipFile, ValueError, KeyError, IndexError):
            continue

    verified = []
    seen_titles = set()
    for u, (root, loc, dt_iso) in list(candidates.items())[:28]:
        title = None
        if db is not None:
            row = db.execute("SELECT title FROM article WHERE url=?", (u,)).fetchone()
            if row:
                title = row[0]
        if not title:
            title = _extract_html_title(u)
        if not title or not VIOLENCE_IMPACT_RE.search(title) or EXCLUDE_RE.search(title):
            continue
        norm_t = re.sub(r"\W+", " ", title.lower()).strip()
        if norm_t in seen_titles:
            continue
        seen_titles.add(norm_t)
        label = CAMEO_LABELS.get(root, "Armed Conflict & Unrest")
        verified.append({
            "kind": "GDELT Live Event",
            "title": title,
            "summary": f"{label} · {clean(loc)}",
            "url": u,
            "level": "Alert" if root in ("19", "20") else "Caution",
            "date": dt_iso,
            "_loc": f"{loc} {title}".lower(),
        })
    print(f"crisis: GDELT 2.0 verified {len(verified)} real-time violent events (from {len(candidates)} candidates)")
    return verified


def _acled_events(now):
    """Optional ACLED API integration when ACLED_API_KEY and ACLED_EMAIL environment variables are set."""
    key = os.environ.get("ACLED_API_KEY", "").strip()
    email = os.environ.get("ACLED_EMAIL", "").strip()
    if not key or not email:
        return []
    since = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    params = urllib.parse.urlencode({
        "key": key,
        "email": email,
        "event_date": since,
        "event_date_where": ">=",
        "event_type": "Battles|Explosions/Remote violence|Violence against civilians|Riots",
        "limit": 150,
    })
    status, body = fetch.get(f"{ACLED_API}?{params}")
    if status != 200 or not body:
        return []
    try:
        rows = json.loads(body.decode("utf-8", errors="replace")).get("data") or []
    except ValueError:
        return []
    out = []
    for r in rows:
        notes = clean((r.get("notes") or "").strip())
        if not notes:
            continue
        ev_type = r.get("sub_event_type") or r.get("event_type") or "Conflict event"
        loc = ", ".join(filter(None, [r.get("location"), r.get("admin1"), r.get("country")]))
        fat = int(r.get("fatalities") or 0)
        fat_str = f" · {fat} reported fatalities" if fat > 0 else ""
        ev_date = r.get("event_date")
        dt_iso = f"{ev_date}T00:00:00+00:00" if ev_date else now.isoformat(timespec="seconds")
        out.append({
            "kind": "ACLED",
            "title": f"{ev_type} in {loc}{fat_str}",
            "summary": notes,
            "url": "https://acleddata.com/",
            "level": "Warning" if fat >= 5 else "Alert",
            "date": dt_iso,
            "_loc": f"{r.get('country', '')} {loc} {notes}".lower(),
        })
    print(f"crisis: ACLED returned {len(out)} events")
    return out


def _dedup_and_cap(items):
    seen = set()
    green_counts = {}
    out = []
    for i in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        key = (i["kind"], i["title"].lower())
        if key in seen:
            continue
        if i["kind"] == "GDACS" and (i.get("level") or "").lower() == "green":
            gkey = re.sub(r"\d+", "", i["title"].lower())
            green_counts[gkey] = green_counts.get(gkey, 0) + 1
            if green_counts[gkey] > 2:
                continue
        seen.add(key)
        out.append(i)
    return out


def run(db=None):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=RECENT_DAYS)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)
    gdacs, usgs, eonet, us = _feed(GDACS), _feed(USGS), _eonet(), _feed(US)
    cg, un, hrw, lwj, msf = _feed(CRISISGROUP), _feed(UN_PEACE), _feed(HRW), _feed(LWJ), _feed(MSF)
    gdelt = _gdelt_events(now, db)
    acled = _acled_events(now)

    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        country_names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", []), *REGIONAL_COUNTRIES.get(cid, [])]]
        mention_terms = [m.lower() for m in pack.get("mention", []) if len(m) >= 4]
        all_names = list(dict.fromkeys([*country_names, *mention_terms[:18]]))

        has_country = lambda text: any(re.search(rf"\b{re.escape(n)}\b", (text or "").lower()) for n in country_names)
        has_any = lambda text: any(re.search(rf"\b{re.escape(n)}\b", (text or "").lower()) for n in all_names)

        items = []
        items += [_item("GDACS", e, e.get("gdacs_alertlevel")) for e in gdacs if has_country(e.get("gdacs_country")) or has_country(e.title)]
        items += [_item("USGS", e) for e in usgs if has_country(e.title)]
        for ev in eonet:
            if has_country(ev.get("title")):
                cat = ((ev.get("categories") or [{}])[0]).get("title") or "Natural event"
                src_url = ((ev.get("sources") or [{}])[0]).get("url") or ev.get("link") or ""
                dt = ((ev.get("geometry") or [{}])[-1]).get("date")
                items.append({"kind": "NASA EONET", "title": clean(ev["title"]), "summary": clean(cat), "url": src_url, "level": None, "date": dt})

        # Conflict, human rights, insurgency, and humanitarian monitors (last 30 days).
        for kind, feed_entries, lvl in (
            ("UN Peace & Security", un, "Security"),
            ("Crisis Group", cg, "Alert"),
            ("Human Rights Watch", hrw, "Alert"),
            ("Long War Journal", lwj, "Security"),
            ("MSF Crisis Update", msf, "Alert"),
        ):
            for e in feed_entries:
                if has_any(e.title) or has_country(e.get("summary")):
                    it = _item(kind, e, lvl)
                    if it["date"] and datetime.fromisoformat(it["date"]) >= cutoff_30d:
                        items.append(it)

        # Real-time GDELT 2.0 and optional ACLED events matched to this desk.
        for ev in gdelt:
            if has_any(ev["_loc"]):
                items.append({k: v for k, v in ev.items() if k != "_loc"})
        for ev in acled:
            if has_any(ev["_loc"]):
                items.append({k: v for k, v in ev.items() if k != "_loc"})

        # US travel advisories: keep active Level 3/4 updated in last 90d, or Level 2 updated in last 30d with conflict/terror risk.
        for e in us:
            if has_country(e.title.split(" - ")[0]) and "Level 1" not in e.title:
                lvl = "Warning" if "Level 4" in e.title else ("Alert" if "Level 3" in e.title else "Caution")
                it = _item("US travel advisory", e, lvl)
                if not it["date"]:
                    continue
                dt = datetime.fromisoformat(it["date"])
                if lvl in ("Warning", "Alert") and dt >= cutoff_90d:
                    items.append(it)
                elif lvl == "Caution" and dt >= cutoff_30d and re.search(r"\b(terror|unrest|conflict|kidnap|armed|violence)\b", (it["summary"] or "").lower()):
                    items.append(it)

        # Include UK travel advice updates within the last 30 days.
        uk_slug = UK_SLUGS[cid] if cid in UK_SLUGS else (pack.get("uk_slug") or pack["name"].lower().replace(" ", "-"))
        if uk_slug:
            uk = [_item("UK travel advice", e) for e in _feed(UK.format(uk_slug))[:3]]
            items += [i for i in uk if i["date"] and datetime.fromisoformat(i["date"]) >= cutoff_30d]

        # Disasters older than a week are history; conflict monitors and active advisories keep their window.
        items = [
            i for i in items
            if i["kind"] not in ("GDACS", "USGS", "NASA EONET")
            or (i["date"] and datetime.fromisoformat(i["date"]) >= recent)
        ]
        out[cid] = _dedup_and_cap(items)
        print(f"crisis: {cid}: {len(out[cid])} items")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("crisis", {"generated_at": now.isoformat(timespec="seconds"), "countries": out}, "ARGOS_CRISIS")

