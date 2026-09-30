"""Stage: keep only articles that are about Vietnam or involve Vietnam.

Rule (no LLM):
- Domestic outlets, in any section except the world/international one: relevant by default.
- World sections of domestic outlets, and every abroad_vi / international outlet: relevant only if
  Vietnam is mentioned in the headline or lead, or at least twice in the article text.
"""
import re

MENTION = re.compile(
    r"vi[eệ]t\s?nam|vietnamese|việt kiều|người việt|gốc việt|h[aà]\s?n[oộ]i|hà nội|ho chi minh|hồ chí minh|tp\.?\s?hcm|tphcm|"
    r"s[aà]i g[oò]n|sài gòn|đà nẵng|da nang|hải phòng|hai phong|mekong|mê ?kông|biển đông|east sea|south china sea",
    re.I)
MIN_TEXT_MENTIONS = 2


def is_relevant(scope, category_hint, section, title, lead, text):
    if scope == "domestic" and category_hint != "foreign_policy":
        return True
    if section == "Việt Nam":            # e.g. RFI's Vietnam section
        return True
    if MENTION.search(f"{title} {lead}"):
        return True
    return len(MENTION.findall(text or "")) >= MIN_TEXT_MENTIONS


def run(db):
    rows = db.execute(
        "SELECT a.id, s.scope, f.category_hint, f.section_label, a.title, a.lead, a.text "
        "FROM article a JOIN source s ON s.id=a.source_id LEFT JOIN feed f ON f.id=a.feed_id").fetchall()
    keep = [(int(is_relevant(r["scope"], r["category_hint"], r["section_label"], r["title"], r["lead"], r["text"])), r["id"])
            for r in rows]
    db.executemany("UPDATE article SET vn_relevant=? WHERE id=?", keep)
    db.commit()
    print(f"relevance: {sum(k for k, _ in keep)} of {len(rows)} articles are about or involve Vietnam")
    q = ("SELECT s.scope, SUM(a.vn_relevant), COUNT(*) FROM article a JOIN source s ON s.id=a.source_id GROUP BY 1")
    for scope, kept, total in db.execute(q):
        print(f"  {scope:14} {kept} / {total}")
