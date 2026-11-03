"""Stage 7: write the data files the website reads (site/data/*.json).

One file per country and time window. Only headlines, short verified excerpts and links are exported:
no full article text ever leaves the local database.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from . import packs
from .config import ROOT
from .rank import dashboard_story_ids

SITE_DATA = ROOT / "site" / "data"
WINDOWS = {1: "24h", 7: "7d"}
PERIOD_LABELS = {"24h": "Last 24 hours", "7d": "Last 7 days"}
CATEGORIES = ["internal_politics", "economics", "foreign_policy", "defence_security", "society", "other"]
MAX_ARTICLES_LISTED = 12

DISASTER_RULES = [
    ("Storm & Cyclone", r"\b(typhoon|cyclone|hurricane|tropical storm|tornado|gale|bão|siêu bão|áp thấp nhiệt đới|lốc xoáy|taufan|badai|bagyo|พายุ|မုန်တိုင်း|vihar|orkán|burza|tufão|ciclone|fırtına|kasırga)\b"),
    ("Flood & Landslide", r"\b(flood|floods|flooding|flash flood|landslide|mudslide|inundation|lũ|lũ lụt|ngập lụt|ngập sâu|sạt lở|triều cường|banjir|longsor|baha|guho|น้ำท่วม|ดินถล่ม|ရေကြီး|árvíz|powódź|poplava|sel\b|heyelan|enchente|deslizamento)"),
    ("Earthquake & Volcano", r"\b(earthquake|tremor|seismic|tsunami|volcano|volcanic|eruption|động đất|núi lửa|sóng thần|gempa|gunung berapi|lindol|bulkan|แผ่นดินไหว|ငလျင်|földrengés|trzęsienie ziemi|zemljotres|deprem|yanardağ|terremoto|zəlzələ)"),
    ("Wildfire & Drought", r"\b(wildfire|forest fire|bushfire|drought|heatwave|cháy rừng|hạn hán|kebakaran hutan|kekeringan|ไฟป่า|ภัยแล้ง|erdőtűz|aszály|pożar lasu|suša|orman yangını|kuraklık|incêndio florestal|seca\b)"),
]

VIOLENCE_RULES = [
    ("Armed Clash & Battle", r"\b(armed clash|gunbattle|firefight|insurgent|insurgency|rebel|militia|junta troops|ambush|skirmish|giao tranh|đụng độ|phiến quân|kontak tembak|kelompok bersenjata|sagupaan|npa\b|ปะทะ|กองกำลัง|တိုက်ပွဲ|စစ်ကောင်စီ|összecsapás|sukob|çatışma|pkk\b|confronto armado|facção|fano\b|endf\b|al-shabaab)"),
    ("Explosion & Strike", r"\b(airstrike|air strike|drone strike|shelling|missile strike|artillery|mortar|ied\b|landmine|car bomb|bombing|không kích|pháo kích|tên lửa|đánh bom|serangan udara|rudal|ledakan bom|โจมตีทางอากาศ|ระเบิด|လေကြောင်းတိုက်ခိုက်|légicsapás|rakétatámadás|robbanás|nalot|hava saldırısı|patlama|bombalı)"),
    ("Terrorism & Attack", r"\b(terrorist|terrorism|suicide attack|gunman|gunmen|mass shooting|shooting|massacre|hostage|assassinat|armed attack|khủng bố|xả súng|teroris|terorisme|penembakan|terorista|pamamaril|ก่อการร้าย|กราดยิง|အကြမ်းဖက်|merénylet|terrortámadás|lövöldözés|zamach|terör|silahlı saldırı|atentado|tiroteio|chacina)"),
    ("Protest & Riot", r"\b(riot|riots|violent protest|tear gas|water cannon|clash with police|demonstration|protesters|civil unrest|biểu tình|bạo động|unjuk rasa|kerusuhan|gas air mata|kilos-protesta|ชุมนุม|ประท้วง|ဆန္ဒပြ|tüntetés|zavargás|könnygáz|zamieszki|protest|gösteri|protesto|საპროტესტო|акция протеста)"),
]


def _classify_events(s):
    themes = " ".join(s.get("themes") or []).lower()
    if "sport" in themes or "culture" in themes:
        return None, None
    blob = " ".join([s["headline"]["title"], *(r["title"] for r in (s.get("sources") or [])[:4])]).lower()
    d_type = next((label for label, pat in DISASTER_RULES if re.search(pat, blob)), None)
    v_type = next((label for label, pat in VIOLENCE_RULES if re.search(pat, blob)), None)
    return d_type, v_type


def _story(db, s):
    rows = db.execute(
        "SELECT a.id, a.title, a.lead, a.url, a.language, a.published_at, a.syndicated_of, COALESCE(sa.similarity, 1.0) AS similarity, "
        "src.id AS source_id, src.name AS source, src.scope, src.kind "
        "FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source src ON src.id=a.source_id "
        "WHERE sa.story_id=? ORDER BY (COALESCE(sa.similarity, 1.0) >= 0.93) DESC, (COALESCE(sa.similarity, 1.0) >= 0.85) DESC, "
        "(a.syndicated_of IS NOT NULL), COALESCE(sa.similarity, 1.0) DESC, a.published_at", (s["id"],)).fetchall()
    core_rows = [r for r in rows if r["similarity"] >= 0.93] or rows
    independent = {r["source_id"] for r in core_rows if r["syndicated_of"] is None}
    by_scope = {sc: sum(r["scope"] == sc for r in core_rows) for sc in ("domestic", "abroad_local", "international")}
    rep = next((r for r in rows if r["id"] == s["representative_article_id"]), rows[0])
    raw_lead = (rep["lead"] or "").strip() or next(((r["lead"] or "").strip() for r in rows if (r["lead"] or "").strip()), "")
    lead_val = (raw_lead[:220].rsplit(" ", 1)[0] + "…") if len(raw_lead) > 220 else raw_lead
    excerpts = db.execute(
        "SELECT x.id, x.text, a.url, src.name AS source, src.scope FROM excerpt x JOIN article a ON a.id=x.article_id "
        "JOIN source src ON src.id=a.source_id WHERE x.story_id=? ORDER BY x.id", (s["id"],)).fetchall()
    related = db.execute(
        "SELECT o.id, a.title, a.url, src.name AS source, (SELECT COUNT(*) FROM story_article WHERE story_id=r.related_id AND COALESCE(similarity, 1.0) >= 0.93) AS n "
        "FROM story_related r JOIN story o ON o.id=r.related_id JOIN article a ON a.id=o.representative_article_id "
        "JOIN source src ON src.id=a.source_id WHERE r.story_id=? ORDER BY r.similarity DESC LIMIT 4", (s["id"],)).fetchall()
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    dated = sorted((r for r in core_rows if r["published_at"]), key=lambda r: r["published_at"])
    days = {}
    for r in dated:
        days[r["published_at"][:10]] = days.get(r["published_at"][:10], 0) + 1
    b_high = [r for r in rows if r["similarity"] >= 0.93][:10]
    b_mid = [r for r in rows if 0.85 <= r["similarity"] < 0.93][:8]
    b_low = [r for r in rows if r["similarity"] < 0.85][:6]
    listed = b_high + b_mid + b_low
    return {
        "id": s["id"],
        "first": {"source": dated[0]["source"], "at": dated[0]["published_at"]} if dated else None,   # earliest article in the story
        "per_day": sorted(days.items()),
        "last_24h": sum(r["published_at"] >= cutoff_24h for r in dated),   # articles in the last day: new, growing or quiet
        "category": s["category"],
        "score": s["score"],
        "themes": json.loads(s["themes"] or "[]"),         # why it ranks where it does (themes.yaml)
        "headline": {"title": rep["title"], "url": rep["url"], "source": rep["source"], "language": rep["language"]},
        "lead": lead_val,
        "first_seen": s["first_seen"],
        "last_seen": s["last_seen"],
        "articles": len(rows),
        "independent_sources": len(independent),
        "by_scope": by_scope,
        "evidence": "OFFICIAL" if any(r["kind"] == "official" for r in core_rows) else "REPORTED",
        "abroad_only": False,
        "related": [{"title": r["title"], "url": r["url"], "source": r["source"], "articles": r["n"]} for r in related[:2]],   # possibly the same event
        "excerpts": [{"text": x["text"], "source": x["source"], "scope": x["scope"], "url": x["url"]} for x in excerpts],
        "sources": [{"title": r["title"], "url": r["url"], "source": r["source"], "scope": r["scope"],
                     "language": r["language"], "published": r["published_at"], "copy": r["syndicated_of"] is not None,
                     "sim": int(round(r["similarity"] * 100))}
                    for r in listed],
    }


def _write(name, payload, var):
    """Write <name>.json, and <name>.js which sets a global. The page loads the .js through a script tag,
    because browsers refuse to fetch() local files when the page is opened straight from a folder."""
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    (SITE_DATA / f"{name}.json").write_text(text, encoding="utf8")
    head = f'window.{var} = window.{var} || {{}}; window.{var}["{name}"] = {text};' if var == "ARGOS_DATA" else f"window.{var} = {text};"
    (SITE_DATA / f"{name}.js").write_text(head + "\n", encoding="utf8")


def _top_global_and_regional(items, key, g_limit, r_limit=6):
    ranked = sorted(items, key=key, reverse=True)
    out, seen, r_counts = [], set(), {}
    for s in ranked[:g_limit]:
        out.append(s)
        seen.add(s["id"])
    for s in ranked:
        reg = s.get("region") or "Other"
        if r_counts.get(reg, 0) < r_limit:
            r_counts[reg] = r_counts.get(reg, 0) + 1
            if s["id"] not in seen:
                out.append(s)
                seen.add(s["id"])
    return out


def _home(now, countries):
    """Build a compact cross-country overview (site/data/home.json) so the front page stays fast at 100+ countries."""
    pool, desks = [], []
    for c in countries:
        cid = c["id"]
        reg = c.get("region", "Other")
        f7 = SITE_DATA / f"{cid}-7d.json"
        f24 = SITE_DATA / f"{cid}-24h.json"
        d7 = json.loads(f7.read_text(encoding="utf8")) if f7.exists() else {"stories": [], "totals": {}}
        d24 = json.loads(f24.read_text(encoding="utf8")) if f24.exists() else {"stories": [], "totals": {}}
        for s in d7["stories"]:
            d_type, v_type = _classify_events(s)
            pool.append({**s, "country": cid, "country_name": c["name"], "region": reg,
                         "disaster_type": d_type, "violence_type": v_type,
                         "excerpts": s.get("excerpts", [])[:1], "sources": s.get("sources", [])[:12]})
        top = d7["stories"][0] if d7["stories"] else None
        desks.append({
            "id": cid, "name": c["name"], "region": reg,
            "stories_24h": sum(d24.get("totals", {}).values()) or len(d24["stories"]),
            "stories_7d": sum(d7.get("totals", {}).values()) or len(d7["stories"]),
            "lead": {"title": top["headline"]["title"], "url": top["headline"]["url"], "source": top["headline"]["source"],
                     "outlets": top["independent_sources"]} if top else None,
        })
    most = _top_global_and_regional(pool, lambda s: (s["independent_sources"], s["score"]), 8)
    growing = _top_global_and_regional((s for s in pool if (s.get("last_24h") or 0) >= 2), lambda s: (s.get("last_24h") or 0, s["score"]), 6)
    disasters = _top_global_and_regional((s for s in pool if s.get("disaster_type")), lambda s: (s["independent_sources"], s["score"]), 12, r_limit=8)
    violent = _top_global_and_regional((s for s in pool if s.get("violence_type")), lambda s: (s["independent_sources"], s["score"]), 12, r_limit=8)
    return {"generated_at": now, "desks": desks, "most_reported": most, "abroad_only": [],
            "growing": growing, "disasters": disasters, "violent_events": violent}


def run(db):
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    countries = []
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        periods = []
        for days, label in WINDOWS.items():
            ids = dashboard_story_ids(db, cid, days)
            if ids:
                stories = [_story(db, db.execute("SELECT * FROM story WHERE id=?", (i,)).fetchone()) for i in ids]
                stories.sort(key=lambda st: -st["score"])
                totals = {c: db.execute("SELECT COUNT(*) FROM story WHERE country=? AND window_days=? AND category=?", (cid, days, c)).fetchone()[0]
                          for c in CATEGORIES}          # all stories found in the window, of which the top ones are exported
                payload = {"country": cid, "period": label, "days": days, "generated_at": now, "categories": CATEGORIES,
                           "totals": totals, "stories": stories}
                _write(f"{cid}-{label}", payload, "ARGOS_DATA")
                print(f"export: {cid}-{label}.json with {len(stories)} stories")
            if ids or (SITE_DATA / f"{cid}-{label}.json").exists():
                periods.append({"id": label, "label": PERIOD_LABELS.get(label, label), "file": f"{cid}-{label}.json"})
        if periods:
            distinctive_mentions = [pack["name"].lower()] + [m.lower() for m in pack.get("mention", [])[:12]]
            countries.append({"id": cid, "name": pack["name"], "region": pack.get("region", "Other"),
                              "language": pack["language"], "abroad_label": pack["abroad_label"],
                              "mentions": list(dict.fromkeys(distinctive_mentions)), "periods": periods})
    keep = ("id", "name", "homepage", "language", "scope", "kind", "governing_body", "state_affiliated", "notes")
    sources_by_country = {c: [{k: s.get(k) for k in keep} for s in packs.load(c)["sources"]] for c in packs.pack_ids()}
    telemetry = {}
    for c in packs.pack_ids():
        p = packs.load(c)
        total_feeds = sum(len(s.get("feeds") or []) for s in p["sources"])
        art_row = db.execute("SELECT COUNT(*), MAX(fetched_at) FROM article WHERE country=?", (c,)).fetchone()
        art_count = art_row[0] if art_row else 0
        last_fetched = art_row[1] if art_row and art_row[1] else now
        telemetry[c] = {
            "total_outlets": len(p["sources"]),
            "total_feeds": total_feeds,
            "articles_indexed": art_count,
            "last_fetched": last_fetched,
            "status": "healthy" if art_count > 0 else "standby"
        }
    _write("sources", {"generated_at": now, "telemetry": telemetry, "sources": sources_by_country}, "ARGOS_SOURCES")
    _write("index", {"generated_at": now, "countries": countries}, "ARGOS_INDEX")
    _write("home", _home(now, countries), "ARGOS_HOME")
