"""Stage 7: write the data files the website reads (site/data/*.json).

One file per country and time window. Only headlines, short verified excerpts and links are exported:
no full article text ever leaves the local database.
"""
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np

from . import packs
from .config import ROOT
from .embed import DIM
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
    ("Insurgency & Terror", r"\b(terror|terrorist|terrorism|insurgent|insurgency|militant|militants|boko haram|iswap|al-shabaab|isis|daesh|jihad|jihadist|taliban|houthi|houthis|hezbollah|hamas|ied|suicide bomb|car bomb|ambush|kidnap|kidnapped|abduct|abducted|hostage|massacre|khủng bố|bắt cóc|phiến quân)\b"),
    ("Armed Clash & Strike", r"\b(airstrike|air strike|drone strike|missile strike|shelling|shelled|mortar|artillery|armed clash|clashes|firefight|gunbattle|gunmen|bombardment|incursion|ceasefire violation|cross-border fire|tập kích|không kích|pháo kích|giao tranh)\b"),
    ("Civil Unrest & Crackdown", r"\b(riot|riots|violent protest|clashes with police|tear gas|water cannon|curfew|martial law|coup|state of emergency|crackdown|mass arrest|looting|arson|bạo loạn|biểu tình|thiết quân luật|đảo chính)\b"),
]
VIOLENCE_EXCLUDE = re.compile(
    r"\b(festival|dance|theatre|theater|concert|music|album|song|singer|film|movie|championship|tournament|league|match|coach|player|stadium|actor|actress|football|soccer|basketball|baseball|cricket|tennis|golf)\b",
    re.I,
)

def _classify_disaster(s):
    themes = " ".join(s.get("themes") or []).lower()
    if "sport" in themes or "culture" in themes:
        return None
    blob = " ".join([s["headline"]["title"], s["headline"].get("en_title") or "", *(r["title"] for r in (s.get("sources") or [])[:4])]).lower()
    return next((label for label, pat in DISASTER_RULES if re.search(pat, blob)), None)

def _classify_violence(s):
    themes = " ".join(s.get("themes") or []).lower()
    if "sport" in themes or "culture" in themes:
        return None
    blob = " ".join([s["headline"]["title"], s["headline"].get("en_title") or "", *(r["title"] for r in (s.get("sources") or [])[:4])]).lower()
    if VIOLENCE_EXCLUDE.search(blob):
        return None
    for label, pat in VIOLENCE_RULES:
        if re.search(pat, blob, re.I):
            return label
    if "civil unrest and armed conflict" in themes or "sectarian and confessional violence" in themes:
        return "Armed Clash & Strike"
    return None


def _prev_window_matches(db, cid, days, prev_start, curr_start):
    """Match relevant articles from the prior window [prev_start, curr_start) to current stories
    via cosine similarity (>= 0.895) against each story's core centroid, and tally prior category counts."""
    prev_rows = db.execute(
        "SELECT a.id, COALESCE(a.published_at, a.fetched_at) AS t, src.scope, src.kind, src.alignment, "
        "f.category_hint, (SELECT s2.category FROM story_article sa2 JOIN story s2 ON s2.id=sa2.story_id "
        "WHERE sa2.article_id=a.id ORDER BY s2.window_days ASC LIMIT 1) AS story_cat, e.vec "
        "FROM article a JOIN source src ON src.id=a.source_id LEFT JOIN feed f ON f.id=a.feed_id "
        "LEFT JOIN embedding e ON e.article_id=a.id "
        "WHERE a.relevant=1 AND a.country=? AND COALESCE(a.published_at, a.fetched_at) >= ? "
        "AND COALESCE(a.published_at, a.fetched_at) < ?",
        (cid, prev_start, curr_start),
    ).fetchall()
    if not prev_rows:
        return {}, Counter()

    s_rows = db.execute(
        "SELECT s.id, s.category, sa.similarity, e.vec "
        "FROM story s JOIN story_article sa ON sa.story_id=s.id JOIN embedding e ON e.article_id=sa.article_id "
        "WHERE s.country=? AND s.window_days=?",
        (cid, days),
    ).fetchall()
    by_s = defaultdict(list)
    s_cat = {}
    for r in s_rows:
        if r["vec"] and len(r["vec"]) == DIM * 4:
            by_s[r["id"]].append(r)
            s_cat[r["id"]] = r["category"]

    sids = list(by_s.keys())
    prev_by_sid = defaultdict(list)
    prev_cats = Counter()

    vec_prev_indices = [i for i, r in enumerate(prev_rows) if r["vec"] and len(r["vec"]) == DIM * 4]
    matched_cat = {}
    if sids and vec_prev_indices:
        centres = []
        for sid in sids:
            core = [r for r in by_s[sid] if (r["similarity"] or 1.0) >= 0.93] or by_s[sid]
            v = np.frombuffer(b"".join(r["vec"] for r in core), dtype=np.float32).reshape(len(core), DIM).mean(0)
            v /= (np.linalg.norm(v) + 1e-9)
            centres.append(v)
        C = np.array(centres, dtype=np.float32)
        P = np.frombuffer(b"".join(prev_rows[i]["vec"] for i in vec_prev_indices), dtype=np.float32).reshape(len(vec_prev_indices), DIM)
        S = P @ C.T
        best_j = np.argmax(S, axis=1)
        best_s = S[np.arange(len(vec_prev_indices)), best_j]
        for local_idx, (j, sim) in enumerate(zip(best_j, best_s)):
            orig_idx = vec_prev_indices[local_idx]
            sid = sids[int(j)]
            if sim >= 0.895:
                prev_by_sid[sid].append((prev_rows[orig_idx], float(sim)))
            if sim >= 0.860:
                matched_cat[orig_idx] = s_cat.get(sid)

    for idx, r in enumerate(prev_rows):
        cat = r["story_cat"] or matched_cat.get(idx) or (r["category_hint"] if r["category_hint"] in CATEGORIES else "other")
        prev_cats[cat if cat in CATEGORIES else "other"] += 1

    return prev_by_sid, prev_cats


def _story(db, s, now_iso=None, days=None, prev_matches=None):
    rows = db.execute(
        "SELECT a.id, a.title, a.lead, a.url, a.language, a.published_at, a.fetched_at, a.syndicated_of, COALESCE(sa.similarity, 1.0) AS similarity, "
        "src.id AS source_id, src.name AS source, src.scope, src.kind, src.bias, src.alignment, src.factuality "
        "FROM story_article sa JOIN article a ON a.id=sa.article_id JOIN source src ON src.id=a.source_id "
        "WHERE sa.story_id=? ORDER BY (COALESCE(sa.similarity, 1.0) >= 0.93) DESC, (COALESCE(sa.similarity, 1.0) >= 0.85) DESC, "
        "(a.syndicated_of IS NOT NULL), COALESCE(sa.similarity, 1.0) DESC, a.published_at", (s["id"],)).fetchall()
    core_rows = [r for r in rows if r["similarity"] >= 0.93] or rows
    independent = {r["source_id"] for r in core_rows if r["syndicated_of"] is None}
    by_scope = {sc: sum(r["scope"] == sc for r in core_rows) for sc in ("domestic", "abroad_local", "international")}

    align_counts, bias_counts = {}, {}
    state_count, total_rated = 0, 0
    for r in core_rows:
        al = r["alignment"] or "unrated"
        bi = r["bias"] or "unrated"
        if al != "unrated":
            align_counts[al] = align_counts.get(al, 0) + 1
        if bi != "unrated":
            bias_counts[bi] = bias_counts.get(bi, 0) + 1
        if al in ("state_controlled", "pro_government") or r["kind"] == "official":
            state_count += 1
        total_rated += 1
    state_share = round(state_count / total_rated, 2) if total_rated else 0.0
    perspectives = {"state_share": state_share, "alignment": align_counts, "bias": bias_counts}

    rep = next((r for r in rows if r["id"] == s["representative_article_id"]), rows[0])
    trans_row = db.execute("SELECT text_en FROM translation WHERE article_id=?", (rep["id"],)).fetchone()
    en_title = trans_row[0] if trans_row else None
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
    days_hist = {}
    for r in dated:
        days_hist[r["published_at"][:10]] = days_hist.get(r["published_at"][:10], 0) + 1
    b_high = [r for r in rows if r["similarity"] >= 0.93][:10]
    b_mid = [r for r in rows if 0.85 <= r["similarity"] < 0.93][:8]
    b_low = [r for r in rows if r["similarity"] < 0.85][:6]
    listed = b_high + b_mid + b_low

    delta = None
    if now_iso and days:
        now_dt = datetime.fromisoformat(now_iso)
        curr_start = (now_dt - timedelta(days=days)).isoformat(timespec="seconds")
        prev_start = (now_dt - timedelta(days=2 * days)).isoformat(timespec="seconds")
        t_curr, t_prev = [], []
        core_t_curr, core_t_prev = [], []
        for r in rows:
            t = r["published_at"] or r["fetched_at"]
            if not t:
                continue
            is_core = (r["similarity"] >= 0.93)
            if t >= curr_start:
                t_curr.append(r)
                if is_core:
                    core_t_curr.append(r)
            elif t >= prev_start and t < curr_start:
                t_prev.append(r)
                if is_core:
                    core_t_prev.append(r)
        if prev_matches:
            seen_prev_ids = {r["id"] for r in t_prev}
            for pr, sim in prev_matches:
                if pr["id"] not in seen_prev_ids:
                    seen_prev_ids.add(pr["id"])
                    t_prev.append(pr)
                    if sim >= 0.910:
                        core_t_prev.append(pr)
        n_curr, n_prev = len(t_curr), len(t_prev)
        delta_n = n_curr - n_prev
        v = round(n_curr / max(1, n_prev), 2)
        if n_prev == 0 and n_curr >= 2:
            st = "new"
        elif delta_n >= 3 and v >= 1.75:
            st = "surging"
        elif -delta_n >= 3 and v <= 0.40:
            st = "cooling"
        elif n_curr >= 2:
            st = "steady"
        else:
            st = "trace"

        scopes_curr = {r["scope"] for r in t_curr}
        scopes_prev = {r["scope"] for r in t_prev}
        if scopes_prev == {"domestic"} and "international" in scopes_curr:
            scope_shift = "international_pickup"
        elif scopes_prev == {"domestic"} and "abroad_local" in scopes_curr and "international" not in scopes_curr:
            scope_shift = "diaspora_pickup"
        else:
            scope_shift = None

        c_state_curr = sum(1 for r in core_t_curr if (r["alignment"] in ("state_controlled", "pro_government") or r["kind"] == "official"))
        c_state_prev = sum(1 for r in core_t_prev if (r["alignment"] in ("state_controlled", "pro_government") or r["kind"] == "official"))
        sh_curr = round(c_state_curr / len(core_t_curr), 2) if core_t_curr else 0.0
        sh_prev = round(c_state_prev / len(core_t_prev), 2) if core_t_prev else 0.0
        state_surge = bool(len(core_t_curr) >= 4 and len(core_t_prev) >= 4 and (sh_curr - sh_prev >= 0.30))
        state_recede = bool(len(core_t_curr) >= 4 and len(core_t_prev) >= 4 and (sh_curr - sh_prev <= -0.30))

        velocity_z = round(float(delta_n) / math.sqrt(max(1.0, float(n_prev))), 2)
        delta = {
            "curr": n_curr, "prev": n_prev, "net": delta_n, "ratio": v, "state": st,
            "velocity_z": velocity_z,
            "scope_shift": scope_shift, "state_share_curr": sh_curr, "state_share_prev": sh_prev,
            "state_surge": state_surge, "state_recede": state_recede
        }

    return {
        "id": s["id"],
        "first": {"source": dated[0]["source"], "at": dated[0]["published_at"]} if dated else None,   # earliest article in the story
        "per_day": sorted(days_hist.items()),
        "last_24h": sum(r["published_at"] >= cutoff_24h for r in dated),   # articles in the last day: new, growing or quiet
        "category": s["category"],
        "score": s["score"],
        "themes": json.loads(s["themes"] or "[]"),         # why it ranks where it does (themes.yaml)
        "headline": {"title": rep["title"], "url": rep["url"], "source": rep["source"], "language": rep["language"], "en_title": en_title},
        "lead": lead_val,
        "first_seen": s["first_seen"],
        "last_seen": s["last_seen"],
        "articles": len(rows),
        "independent_sources": len(independent),
        "by_scope": by_scope,
        "evidence": "OFFICIAL" if any(r["kind"] == "official" for r in core_rows) else "REPORTED",
        "perspectives": perspectives,
        "delta": delta,
        "abroad_only": False,
        "related": [{"title": r["title"], "url": r["url"], "source": r["source"], "articles": r["n"]} for r in related[:2]],   # possibly the same event
        "excerpts": [{"text": x["text"], "source": x["source"], "scope": x["scope"], "url": x["url"]} for x in excerpts],
        "sources": [{"title": r["title"], "url": r["url"], "source": r["source"], "scope": r["scope"],
                     "language": r["language"], "published": r["published_at"], "copy": r["syndicated_of"] is not None,
                     "sim": int(round(r["similarity"] * 100)),
                     "bias": r["bias"] or "unrated", "alignment": r["alignment"] or "unrated", "factuality": r["factuality"] or "unrated"}
                    for r in listed],
    }


def _agenda_delta(db, cid, days, now_iso, prev_cats=None):
    now_dt = datetime.fromisoformat(now_iso)
    curr_start = (now_dt - timedelta(days=days)).isoformat(timespec="seconds")
    prev_start = (now_dt - timedelta(days=2 * days)).isoformat(timespec="seconds")
    q = """
        SELECT s.category,
               SUM(CASE WHEN COALESCE(a.published_at, a.fetched_at) >= ? THEN 1 ELSE 0 END) AS curr_cnt,
               SUM(CASE WHEN COALESCE(a.published_at, a.fetched_at) >= ? AND COALESCE(a.published_at, a.fetched_at) < ? THEN 1 ELSE 0 END) AS prev_cnt
        FROM story_article sa
        JOIN story s ON s.id = sa.story_id
        JOIN article a ON a.id = sa.article_id
        WHERE s.country = ? AND s.window_days = ?
        GROUP BY s.category
    """
    rows = db.execute(q, (curr_start, prev_start, curr_start, cid, days)).fetchall()
    by_cat = {r["category"]: (r["curr_cnt"] or 0, (prev_cats.get(r["category"], 0) if prev_cats is not None else (r["prev_cnt"] or 0))) for r in rows}
    if prev_cats:
        for cat, p_cnt in prev_cats.items():
            if cat not in by_cat:
                by_cat[cat] = (0, p_cnt)
    total_curr = sum(c for c, p in by_cat.values())
    total_prev = sum(p for c, p in by_cat.values())
    agenda = {}
    for cat in CATEGORIES:
        curr, prev = by_cat.get(cat, (0, 0))
        sc = round((curr / total_curr * 100.0), 1) if total_curr else 0.0
        sp = round((prev / total_prev * 100.0), 1) if total_prev else 0.0
        agenda[cat] = {
            "curr": curr, "prev": prev, "net": curr - prev,
            "share_pct": sc, "share_delta_pct": round(sc - sp, 1),
        }
    return agenda


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


_ELECTION_TERMS = ("election", "választás", "bầu cử", "élection", "elección", "wahl", "wybory", "выборы", "seçim", "انتخابات")


def _is_election(s):
    themes_str = " ".join(s.get("themes") or []).lower()
    return any(w in themes_str for w in _ELECTION_TERMS)


def _pick_desk_lead(stories):
    """Prefer substantive policy/news leads over 'other' (e.g. tabloid/entertainment) when available."""
    if not stories:
        return None
    for s in stories:
        if s.get("category") != "other":
            return s
    return stories[0]


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
        surging = 0
        elections_n = 0
        intl_pickups = 0
        for s in d7["stories"]:
            d_type = _classify_disaster(s)
            v_type = _classify_violence(s)
            delta = s.get("delta") or {}
            if delta.get("state") in ("surging", "new"):
                surging += 1
            if _is_election(s):
                elections_n += 1
            if delta.get("scope_shift"):
                intl_pickups += 1
            pool.append({**s, "country": cid, "country_name": c["name"], "region": reg,
                         "disaster_type": d_type, "violence_type": v_type,
                         "excerpts": s.get("excerpts", [])[:1], "sources": s.get("sources", [])[:12]})
        top = _pick_desk_lead(d7["stories"])
        desks.append({
            "id": cid, "name": c["name"], "region": reg,
            "stories_24h": sum(d24.get("totals", {}).values()) or len(d24["stories"]),
            "stories_7d": sum(d7.get("totals", {}).values()) or len(d7["stories"]),
            "surging": surging,
            "elections": elections_n,
            "intl_pickups": intl_pickups,
            "lead": {"title": top["headline"]["title"], "url": top["headline"]["url"], "source": top["headline"]["source"],
                     "outlets": top["independent_sources"], "category": top.get("category"),
                     "is_election": _is_election(top)} if top else None,
        })
    most = _top_global_and_regional(
        pool, lambda s: (s.get("category") != "other", s["independent_sources"], s.get("score") or 0.0), 8)
    growing = _top_global_and_regional(
        (s for s in pool if (s.get("last_24h") or 0) >= 2),
        lambda s: (s.get("category") != "other", s.get("last_24h") or 0, s.get("score") or 0.0), 6)
    elections = _top_global_and_regional(
        (s for s in pool if _is_election(s)),
        lambda s: (s["independent_sources"], s.get("score") or 0.0), 6, r_limit=4)
    disasters = _top_global_and_regional((s for s in pool if s.get("disaster_type")), lambda s: (s["independent_sources"], s.get("score") or 0.0), 12, r_limit=8)
    violent = _top_global_and_regional(
        (s for s in pool if s.get("violence_type")),
        lambda s: (s["independent_sources"], s.get("score") or 0.0), 12, r_limit=8)
    return {"generated_at": now, "desks": desks, "most_reported": most, "abroad_only": [],
            "growing": growing, "elections": elections, "disasters": disasters, "violent_events": violent}


def run(db):
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    countries = []
    for cid in packs.pack_ids():
        pack = packs.load(cid)
        periods = []
        for days, label in WINDOWS.items():
            window_cutoff = (now_dt - timedelta(days=days)).isoformat(timespec="seconds")
            prev_cutoff = (now_dt - timedelta(days=2 * days)).isoformat(timespec="seconds")
            ids = dashboard_story_ids(db, cid, days)
            prev_by_sid, prev_cats = _prev_window_matches(db, cid, days, prev_cutoff, window_cutoff) if ids else ({}, Counter())
            stories = [_story(db, db.execute("SELECT * FROM story WHERE id=?", (i,)).fetchone(), now, days, prev_by_sid.get(i)) for i in ids] if ids else []
            stories = [st for st in stories if (st.get("last_seen") or st.get("first_seen") or "") >= window_cutoff]
            stories.sort(key=lambda st: -(st["score"] or 0.0))
            totals = {c: db.execute("SELECT COUNT(*) FROM story WHERE country=? AND window_days=? AND category=? AND COALESCE(last_seen, first_seen, '') >= ?", (cid, days, c, window_cutoff)).fetchone()[0] if stories else 0
                      for c in CATEGORIES}          # all stories found in the window, of which the top ones are exported
            agenda_delta = _agenda_delta(db, cid, days, now, prev_cats) if stories else None
            payload = {"country": cid, "period": label, "days": days, "generated_at": now, "categories": CATEGORIES,
                       "totals": totals, "agenda_delta": agenda_delta, "stories": stories}
            _write(f"{cid}-{label}", payload, "ARGOS_DATA")
            periods.append({"id": label, "label": PERIOD_LABELS.get(label, label), "file": f"{cid}-{label}.json"})
            if stories:
                print(f"export: {cid}-{label}.json with {len(stories)} stories")
        if periods:
            distinctive_mentions = [pack["name"].lower()] + [m.lower() for m in pack.get("mention", [])[:12]]
            countries.append({"id": cid, "name": pack["name"], "region": pack.get("region", "Other"),
                              "language": pack["language"], "abroad_label": pack["abroad_label"],
                              "mentions": list(dict.fromkeys(distinctive_mentions)), "periods": periods})
    keep = ("id", "name", "homepage", "language", "scope", "kind", "governing_body", "state_affiliated", "notes")
    db_sources = {r["id"]: dict(r) for r in db.execute("SELECT id, bias, alignment, factuality FROM source").fetchall()}
    sources_by_country = {
        c: [
            {**{k: s.get(k) for k in keep},
             "bias": (db_sources.get(s["id"]) or {}).get("bias") or "unrated",
             "alignment": (db_sources.get(s["id"]) or {}).get("alignment") or "unrated",
             "factuality": (db_sources.get(s["id"]) or {}).get("factuality") or "unrated"}
            for s in packs.load(c)["sources"]
        ]
        for c in packs.pack_ids()
    }
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
    for pat in ("*-14d.json", "*-14d.js", "*-30d.json", "*-30d.js"):
        for old in SITE_DATA.glob(pat):
            old.unlink(missing_ok=True)
