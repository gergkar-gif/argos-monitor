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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from . import fetch, packs
from .export import SITE_DATA, _write
from .extract import extract_text
from .ingest import _match_outlet_scope
from .ratings import lookup_rating
from .textutil import clean, clean_url, nfc

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
    "iraq": ["iraqi", "baghdad", "basra", "erbil", "mosul", "kirkuk", "kataib hezbollah"],
    "lebanon": ["hezbollah", "beirut", "litani", "tyre", "sidon", "bekaa"],
    "saudi_arabia": ["yemen", "houthi", "houthis", "sanaa", "hodeidah", "hudaydah", "taiz", "aden", "marib"],
}

UK_SLUGS = {
    "dr_congo": "democratic-republic-of-the-congo",
    "united_states": "usa",
    "united_kingdom": None,
    "czechia": "czech-republic",
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
    r"baseball|golf|tennis|car-crash|road-accident|house-collapse|wife|husband|boyfriend|girlfriend|divorce|faces-court|judge-rejects|bail|"
    r"lion|lioness|lions|tiger|tigress|tigers|leopard|bear|shark|crocodile|elephant|dog|dogs|snake|monkey|zoo|safari|poacher|"
    r"bus-crash|train-crash|drowned|drowning|gala|performs|performed|marks a year|returned hostage|former hostage)\b",
    re.I,
)
UK_SECURITY_RE = re.compile(
    r"\b(terror|attack|conflict|missile|drone|airstrike|strike|clash|unrest|protest|demonstration|riot|curfew|martial|emergency|"
    r"evacuat|border|airspace|shelter|kidnap|hostage|violence|military|security|warning|advise against|earthquake|tsunami|volcano|"
    r"cyclone|typhoon|hurricane|flood|wildfire|landslide|explosion|gunmen|state of emergency)\b",
    re.I,
)
UK_ROUTINE_EXCLUDE_RE = re.compile(
    r"^(Removal of information|New information about entry requirements|Updated information about visa|Updated information about entry|"
    r"Updated information on passport|New information on entry)\b|\b(FIFA|World Cup|festival|Durga Puja|Carnival|Eurovision)\b",
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
    raw = re.sub(r"^Click to expand Image\s*", "", raw, flags=re.I).strip()
    if kind == "USGS":
        loc = re.search(r"Location\s+([0-9.°\sNSWE+-]+?)(?=\s+Depth|\s*$)", raw, re.I)
        dep = re.search(r"Depth\s+([\d.]+\s*km)", raw, re.I)
        parts = [f"Epicenter {loc.group(1).strip()}" if loc else None, f"Depth {dep.group(1).strip()}" if dep else None]
        return " · ".join(p for p in parts if p)
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


_CACHED_GDELT = None


def _extract_html_meta(url):
    status, body = fetch.get(url)
    if status != 200 or not body:
        return None, "", "", None
    head = body[:32768].decode("utf-8", errors="replace")
    m = (
        re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', head, re.I)
        or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', head, re.I)
        or re.search(r"<title[^>]*>([^<]+)</title>", head, re.I)
    )
    if not m:
        return None, "", "", None
    t = clean(html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()))
    suffix_site = ""
    # Strip trailing site-name suffixes (" - Al Jazeera", " | The Manila Times") if headline remains >= 25 chars
    for sep in (" | ", " - ", " — ", " – "):
        if sep in t:
            left, right = t.rsplit(sep, 1)
            if len(left.strip()) >= 25:
                t = left.strip()
                suffix_site = right.strip()
                break
    if len(t) < 20:
        return None, "", "", None
    dm = (
        re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', head, re.I)
        or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:)?description["\']', head, re.I)
    )
    lead = clean(html.unescape(re.sub(r"\s+", " ", dm.group(1)).strip())) if dm else ""
    if len(lead) < 35 or lead.lower() == t.lower():
        lead = ""
    sm = (
        re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']', head, re.I)
        or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:site_name["\']', head, re.I)
    )
    site = clean(html.unescape(sm.group(1).strip())) if sm else suffix_site
    try:
        extracted = extract_text(body)
    except Exception:
        extracted = None
    text = nfc(extracted) if (extracted and len(extracted) > 200) else None
    return t, lead, site, text


def _extract_html_title(url):
    return _extract_html_meta(url)[0]


def _desk_matchers():
    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        primary_names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", [])]]
        regional_names = [n.lower() for n in REGIONAL_COUNTRIES.get(cid, [])]
        country_names = primary_names + regional_names
        mention_terms = [m.lower() for m in pack.get("mention", []) if len(m) >= 4]
        all_names = list(dict.fromkeys([*country_names, *mention_terms[:18]]))
        out[cid] = {
            "pack": pack,
            "primary_re": re.compile(r"\b(?:" + "|".join(re.escape(n) for n in primary_names) + r")\b", re.I) if primary_names else None,
            "regional_re": re.compile(r"\b(?:" + "|".join(re.escape(n) for n in regional_names) + r")\b", re.I) if regional_names else None,
            "country_re": re.compile(r"\b(?:" + "|".join(re.escape(n) for n in country_names) + r")\b", re.I),
            "any_re": re.compile(r"\b(?:" + "|".join(re.escape(n) for n in all_names) + r")\b", re.I),
        }
    return out


def ingest_gdelt_articles(db, events, now=None):
    """Insert verified GDELT 2.0 conflict URLs directly into SQLite `source` and `article` tables
    so they are embedded, excerpted, and clustered with domestic desk stories."""
    if db is None or not events:
        return 0
    now_iso = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    matchers = _desk_matchers()
    added, matched_total = 0, 0
    for ev in events:
        raw_loc = ev.get("_raw_loc") or ev.get("summary") or ""
        title = ev.get("title") or ""
        blob = ev.get("_loc") or f"{raw_loc} {title}".lower()
        scored = []
        for cid, m in matchers.items():
            if not m["any_re"].search(blob):
                continue
            if m["primary_re"] and m["primary_re"].search(raw_loc):
                prio = 3
            elif m["regional_re"] and m["regional_re"].search(raw_loc):
                prio = 2
            elif m["country_re"].search(title):
                prio = 1
            else:
                prio = 0
            scored.append((prio, cid))
        if not scored:
            continue
        scored.sort(key=lambda x: (-x[0], x[1]))
        cid = scored[0][1]
        matched_total += 1
        pack = matchers[cid]["pack"]
        u = clean_url(ev["url"])
        domain = urllib.parse.urlsplit(u).netloc.lower().removeprefix("www.")
        if not domain:
            continue
        matched_src = next(
            (s for s in pack["sources"]
             if urllib.parse.urlsplit(s.get("homepage") or "").netloc.lower().removeprefix("www.") == domain),
            None,
        )
        if matched_src and db.execute("SELECT 1 FROM source WHERE id=?", (matched_src["id"],)).fetchone():
            sid = matched_src["id"]
            lang = matched_src.get("language") or "en"
        else:
            sid = f"gdelt:{domain}"
            outlet = ev.get("_site") or domain
            lang = (matched_src.get("language") if matched_src else None) or "en"
            overrides = {}
            for sc, names in (pack.get("aggregator_outlets") or {}).items():
                overrides.update({n.lower(): sc for n in names})
            geo = (pack.get("geo") or "").lower()
            if matched_src:
                default_scope = matched_src["scope"]
            elif len(geo) == 2 and (domain.endswith(f".{geo}") or f".{geo}." in domain):
                default_scope = "domestic"
            else:
                default_scope = "international"
            scope = (
                _match_outlet_scope(outlet, overrides, None)
                or _match_outlet_scope(domain.split(".")[0], overrides, default_scope)
            )
            rating = lookup_rating(outlet, False, "media")
            if rating["bias"] == "unrated" and outlet != domain:
                rating = lookup_rating(domain, False, "media")
            db.execute(
                "INSERT INTO source (id, name, homepage, language, scope, kind, governing_body, state_affiliated, reprints_vna, notes, bias, alignment, factuality) "
                "VALUES (?,?,?,?,?,'media','found via GDELT 2.0',0,0,'GDELT 2.0 conflict stream',?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET "
                "scope=CASE WHEN (scope='international' AND excluded.scope != 'international') OR (excluded.scope='domestic' AND scope != 'domestic') THEN excluded.scope ELSE scope END, "
                "bias=COALESCE(excluded.bias, bias), alignment=COALESCE(excluded.alignment, alignment), factuality=COALESCE(excluded.factuality, factuality)",
                (sid, outlet, "https://" + domain, lang, scope, rating["bias"], rating["alignment"], rating["factuality"]),
            )
        text = ev.get("_text")
        status = "ok" if (text and len(text) > 200) else "pending"
        cur = db.execute(
            "INSERT OR IGNORE INTO article (source_id,feed_id,url,title,lead,text,language,published_at,fetched_at,extract_status,relevant,country) "
            "VALUES (?,NULL,?,?,?,?,?,?,?,?,1,?)",
            (sid, u, title, ev.get("_lead") or "", text, lang, ev.get("date") or now_iso, now_iso, status, cid),
        )
        if cur.rowcount:
            added += 1
        else:
            db.execute(
                "UPDATE article SET relevant=1, text=COALESCE(text, ?), "
                "extract_status=CASE WHEN text IS NULL AND ? IS NOT NULL THEN 'ok' ELSE extract_status END "
                "WHERE url=?",
                (text, text, u),
            )
    db.commit()
    print(f"crisis: GDELT 2.0 ingested {added} new conflict articles into SQLite ({matched_total} matched to desks)")
    return added


def _gdelt_events(now, db=None, use_cache=False):
    """Fetch recent 15-minute GDELT 2.0 event intervals across a 24h rolling window, filter for
    high-confidence kinetic violence/unrest, verify each event's verbatim source headline (Rule 1),
    and ingest verified URLs into SQLite."""
    global _CACHED_GDELT
    if use_cache and _CACHED_GDELT is not None:
        if db is not None:
            ingest_gdelt_articles(db, _CACHED_GDELT, now)
        return _CACHED_GDELT
    candidates = {}
    # Poll every 15m for the last 3 hours, plus every 60m across the rest of the 24h window
    offsets = list(range(15, 195, 15)) + list(range(240, 1441, 60))
    ts_list = []
    for mins in offsets:
        t = now - timedelta(minutes=mins)
        ts = t.strftime("%Y%m%d%H") + f"{(t.minute // 15) * 15:02d}00"
        if ts not in ts_list:
            ts_list.append(ts)

    def _fetch_z(ts):
        status, zbytes = fetch.get(GDELT_BASE.format(ts))
        return ts, (zbytes if status == 200 else None)

    with ThreadPoolExecutor(max_workers=12) as pool:
        z_results = list(pool.map(_fetch_z, ts_list))

    for ts, zbytes in z_results:
        if not zbytes:
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
                    loc, raw_u = (r[52] or "").strip(), (r[60] or "").strip()
                    if not loc or not raw_u.startswith(("http://", "https://")):
                        continue
                    u = clean_url(raw_u)
                    if not u or u in candidates:
                        continue
                    if ARMED_CONFLICT_RE.search(u) and VIOLENCE_IMPACT_RE.search(u) and not EXCLUDE_RE.search(u):
                        dt_iso = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
                        candidates[u] = (root, loc, dt_iso)
        except (zipfile.BadZipFile, ValueError, KeyError, IndexError):
            continue

    matchers = _desk_matchers()
    ordered_cands = sorted(
        candidates.items(),
        key=lambda kv: (
            not any(m["country_re"].search(f"{kv[1][1]} {kv[0]}") for m in matchers.values()),
            kv[1][0] not in ("19", "20"),
            -int(kv[1][2][:10].replace("-", "")),
        ),
    )[:55]

    pre_titles = {}
    if db is not None:
        for u, _ in ordered_cands:
            row = db.execute("SELECT title, lead, text FROM article WHERE url=?", (u,)).fetchone()
            if row and row[0]:
                pre_titles[u] = (row[0], row[1] or "", "", row[2])

    to_fetch = [u for u, _ in ordered_cands if u not in pre_titles]
    with ThreadPoolExecutor(max_workers=12) as pool:
        fetched_meta = dict(zip(to_fetch, pool.map(_extract_html_meta, to_fetch)))

    verified = []
    seen_titles = set()
    for u, (root, loc, dt_iso) in ordered_cands:
        title, lead, site, text = pre_titles.get(u) or fetched_meta.get(u) or (None, "", "", None)
        if (
            not title
            or len(title) > 190
            or title.count(";") >= 3
            or not ARMED_CONFLICT_RE.search(title)
            or not VIOLENCE_IMPACT_RE.search(title)
            or EXCLUDE_RE.search(title)
        ):
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
            "_raw_loc": loc,
            "_lead": lead,
            "_site": site,
            "_text": text,
        })
    print(f"crisis: GDELT 2.0 verified {len(verified)} real-time violent events (from {len(candidates)} candidates)")
    if db is not None:
        ingest_gdelt_articles(db, verified, now)
    _CACHED_GDELT = verified
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


_STOP_TOKENS = {
    "attack", "attacks", "strike", "strikes", "clash", "clashes", "killed", "kills", "kill", "killing",
    "dead", "death", "over", "after", "with", "from", "into", "amid", "says", "said", "report", "reports",
    "news", "more", "than", "least", "three", "four", "five", "amid", "against", "under", "near",
}


def _sig_tokens(title):
    words = re.findall(r"[a-z0-9]{4,}", (title or "").lower())
    return {w.rstrip("s") for w in words if w not in _STOP_TOKENS and len(w.rstrip("s")) >= 3}


def _dedup_and_cap(items, max_items=5):
    seen = set()
    seen_toks = []
    out = []
    for i in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        key = (i["kind"], i["title"].lower())
        if key in seen:
            continue
        toks = _sig_tokens(i["title"])
        if len(toks) >= 2 and any(
            len(toks & prev) >= 2 and len(toks & prev) / max(1, min(len(toks), len(prev))) >= 0.5
            for prev in seen_toks
        ):
            continue
        seen.add(key)
        if toks:
            seen_toks.append(toks)
        out.append(i)
        if len(out) >= max_items:
            break
    return out


def _prev_gdelt_items(recent_iso):
    f = SITE_DATA / "crisis.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf8"))
    except Exception:
        return []
    seen_urls = set()
    kept = []
    for items in (data.get("countries") or {}).values():
        for it in items:
            if it.get("kind") != "GDELT Live Event":
                continue
            u = it.get("url")
            dt = it.get("date") or ""
            title = it.get("title") or ""
            if (
                not u
                or u in seen_urls
                or dt < recent_iso
                or len(title) > 190
                or title.count(";") >= 3
                or not ARMED_CONFLICT_RE.search(title)
                or not VIOLENCE_IMPACT_RE.search(title)
                or EXCLUDE_RE.search(title)
            ):
                continue
            seen_urls.add(u)
            kept.append({
                **it,
                "_loc": f"{it.get('summary') or ''} {title}".lower(),
                "_raw_loc": (it.get("summary") or "").split("·")[-1].strip(),
            })
    return kept


def run(db=None):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=RECENT_DAYS)
    recent_iso = recent.isoformat(timespec="seconds")
    cutoff_14d = now - timedelta(days=14)

    feed_urls = {
        "gdacs": GDACS,
        "usgs": USGS,
        "us": US,
        "cg": CRISISGROUP,
        "un": UN_PEACE,
        "hrw": HRW,
        "lwj": LWJ,
        "msf": MSF,
    }
    uk_slugs_by_cid = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        uk_slug = UK_SLUGS[cid] if cid in UK_SLUGS else (pack.get("uk_slug") or pack["name"].lower().replace(" ", "-"))
        if uk_slug:
            uk_slugs_by_cid[cid] = uk_slug

    with ThreadPoolExecutor(max_workers=16) as pool:
        f_futures = {k: pool.submit(_feed, u) for k, u in feed_urls.items()}
        eonet_fut = pool.submit(_eonet)
        uk_futures = {cid: pool.submit(_feed, UK.format(slug)) for cid, slug in uk_slugs_by_cid.items()}
        f_res = {k: fut.result() for k, fut in f_futures.items()}
        eonet = eonet_fut.result()
        uk_res = {cid: fut.result() for cid, fut in uk_futures.items()}

    gdacs, usgs, us = f_res["gdacs"], f_res["usgs"], f_res["us"]
    cg, un, hrw, lwj, msf = f_res["cg"], f_res["un"], f_res["hrw"], f_res["lwj"], f_res["msf"]
    fresh_gdelt = _gdelt_events(now, db, use_cache=True)
    prev_gdelt = _prev_gdelt_items(recent_iso)
    seen_gdelt_urls = {ev["url"] for ev in fresh_gdelt}
    gdelt = fresh_gdelt + [ev for ev in prev_gdelt if ev["url"] not in seen_gdelt_urls]
    acled = _acled_events(now)

    out = {}
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        country_names = [n.lower() for n in [pack["name"], *pack.get("crisis_names", []), *REGIONAL_COUNTRIES.get(cid, [])]]
        mention_terms = [m.lower() for m in pack.get("mention", []) if len(m) >= 4]
        all_names = list(dict.fromkeys([*country_names, *mention_terms[:18]]))

        def has_country(text):
            low = (text or "").lower()
            if cid == "lebanon" and "kataib hezbollah" in low and "lebanon" not in low and "beirut" not in low:
                return False
            return any(re.search(rf"\b{re.escape(n)}\b", low) for n in country_names)
        has_any = lambda text: any(re.search(rf"\b{re.escape(n)}\b", (text or "").lower()) for n in all_names)

        items = []
        # GDACS: keep Orange and Red disaster alerts, plus named cyclones/tsunamis (drop routine Green brush fire notifications).
        for e in gdacs:
            if not (has_country(e.get("gdacs_country")) or has_country(e.title)):
                continue
            lvl = (e.get("gdacs_alertlevel") or "").strip()
            t_low = (e.title or "").lower()
            if lvl.lower() == "green" and not re.search(r"\b(cyclone|typhoon|hurricane|tsunami)\b", t_low):
                continue
            items.append(_item("GDACS", e, lvl or "Alert"))

        # USGS: keep significant earthquakes M5.0+ (filter out minor M4.5-4.9 tremors).
        for e in usgs:
            if not has_country(e.title):
                continue
            m_mag = re.search(r"\bM\s*(\d+(?:\.\d+)?)\b", e.title or "")
            mag = float(m_mag.group(1)) if m_mag else 0.0
            if mag < 5.0:
                continue
            lvl = "Warning" if mag >= 6.0 else ("Alert" if mag >= 5.5 else "Caution")
            items.append(_item("USGS", e, lvl))

        for ev in eonet:
            if has_country(ev.get("title")):
                cat = ((ev.get("categories") or [{}])[0]).get("title") or "Natural event"
                src_url = ((ev.get("sources") or [{}])[0]).get("url") or ev.get("link") or ""
                dt = ((ev.get("geometry") or [{}])[-1]).get("date")
                items.append({"kind": "NASA EONET", "title": clean(ev["title"]), "summary": clean(cat), "url": src_url, "level": "Caution", "date": dt})

        # Conflict, human rights, insurgency, and humanitarian monitors (last 7 days; match headline to avoid summary false positives).
        for kind, feed_entries, lvl in (
            ("UN Peace & Security", un, "Security"),
            ("Crisis Group", cg, "Alert"),
            ("Human Rights Watch", hrw, "Alert"),
            ("Long War Journal", lwj, "Security"),
            ("MSF Crisis Update", msf, "Alert"),
        ):
            for e in feed_entries:
                if has_country(e.title):
                    it = _item(kind, e, lvl)
                    if it["date"] and datetime.fromisoformat(it["date"]) >= recent:
                        items.append(it)

        # Real-time GDELT 2.0 and optional ACLED events matched to this desk (require primary/regional country match in title or location+title).
        for ev in gdelt:
            if has_country(ev.get("title")) or (has_country(ev.get("_raw_loc")) and has_any(ev.get("title"))):
                items.append({k: v for k, v in ev.items() if not k.startswith("_")})
        for ev in acled:
            if has_country(ev["_loc"]):
                items.append({k: v for k, v in ev.items() if not k.startswith("_")})

        # US travel advisories: keep Level 3/4 updated in last 14d, or Level 2 updated in last 7d with conflict/terror risk.
        for e in us:
            if has_country(e.title.split(" - ")[0]) and "Level 1" not in e.title:
                lvl = "Warning" if "Level 4" in e.title else ("Alert" if "Level 3" in e.title else "Caution")
                it = _item("US travel advisory", e, lvl)
                if not it["date"]:
                    continue
                dt = datetime.fromisoformat(it["date"])
                if lvl in ("Warning", "Alert") and dt >= cutoff_14d:
                    items.append(it)
                elif lvl == "Caution" and dt >= recent and re.search(r"\b(terror|unrest|conflict|kidnap|armed|violence)\b", (it["summary"] or "").lower()):
                    items.append(it)

        # UK travel advice updates within the last 7 days with security/crisis relevance.
        for e in (uk_res.get(cid) or [])[:3]:
            it = _item("UK travel advice", e, "Caution")
            if (
                it["date"]
                and datetime.fromisoformat(it["date"]) >= recent
                and UK_SECURITY_RE.search(it["title"])
                and not UK_ROUTINE_EXCLUDE_RE.search(it["title"])
            ):
                items.append(it)

        items = [i for i in items if i.get("date") and datetime.fromisoformat(i["date"]) >= (cutoff_14d if i["kind"] == "US travel advisory" else recent)]
        out[cid] = _dedup_and_cap(items, max_items=5)
        print(f"crisis: {cid}: {len(out[cid])} items")
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    _write("crisis", {"generated_at": now.isoformat(timespec="seconds"), "countries": out}, "ARGOS_CRISIS")

