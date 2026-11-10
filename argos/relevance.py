"""Stage: keep only articles that are about the country or involve it. The country's words come from its pack.

Rule (no LLM):
- A skipped section (sport, culture, lifestyle: see url_sections in pack.yaml) is never relevant.
- A domestic outlet's article is relevant by default, unless its feed section or its web address says it is a
  foreign or world section.
- A source marked needs_mention (its addresses show no section) is treated like a world section.
- Everything else (world sections, outlets abroad, international outlets) is relevant only if the country is
  mentioned in the headline or summary, or at least twice in the article text.
"""
from . import packs

MIN_TEXT_MENTIONS = 2


def is_relevant(pack, scope, category_hint, section, url, title, lead, text, needs_mention=False, is_gdelt=False):
    sections = packs.url_sections(url)
    if sections & pack["skip_sections"]:
        return False
    if is_gdelt:
        return True
    is_foreign = bool(sections & pack["foreign_sections"]) or bool(section and section.lower() in pack["foreign_sections"])
    if scope == "domestic" and not needs_mention and category_hint != "foreign_policy" and not is_foreign:
        return True
    if pack.get("mention_section") and section == pack["mention_section"]:   # e.g. RFI's own Vietnam section
        return True
    if pack["mention_re"].search(f"{title} {lead}"):
        return True
    return len(pack["mention_re"].findall(text or "")) >= MIN_TEXT_MENTIONS


def run(db):
    rows = db.execute(
        "SELECT a.id, a.country, a.source_id, a.feed_id, f.source_id AS feed_source, a.url, s.scope, f.category_hint, f.section_label, a.title, a.lead, a.text "
        "FROM article a JOIN source s ON s.id=a.source_id LEFT JOIN feed f ON f.id=a.feed_id").fetchall()
    needs = {s["id"]: s.get("needs_mention", False) for c in packs.pack_ids() for s in packs.load(c)["sources"]}
    keep = []
    for r in rows:
        pack = packs.load(r["country"])
        is_gdelt = r["feed_id"] is None or (r["source_id"] or "").startswith("gdelt:")
        keep.append((int(is_relevant(pack, r["scope"], r["category_hint"], r["section_label"], r["url"],
                                     r["title"], r["lead"], r["text"], needs.get(r["source_id"], False) or needs.get(r["feed_source"], False),
                                     is_gdelt=is_gdelt)), r["id"]))
    db.executemany("UPDATE article SET relevant=? WHERE id=?", keep)
    db.commit()
    print(f"relevance: {sum(k for k, _ in keep)} of {len(rows)} articles are about or involve their country")
    q = ("SELECT a.country, s.scope, SUM(a.relevant), COUNT(*) FROM article a JOIN source s ON s.id=a.source_id "
         "GROUP BY 1, 2 ORDER BY 1, 2")
    for country, scope, kept, total in db.execute(q):
        print(f"  {country:9} {scope:13} {kept} / {total}")
