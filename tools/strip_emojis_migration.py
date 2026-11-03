"""One-time migration: strip legacy emojis from previously stored articles in SQLite.
Run: python tools/strip_emojis_migration.py [--dry-run]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from argos.config import DB_PATH
from argos.textutil import EMOJI_RE


def strip_em(s):
    """Strip emojis and collapse any double spaces left behind, preserving non-emoji text."""
    if not s or not EMOJI_RE.search(s):
        return s
    cleaned = EMOJI_RE.sub("", s)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def strip_body(s):
    """Strip emojis from article body text without touching newlines or paragraph breaks."""
    if not s or not EMOJI_RE.search(s):
        return s
    return EMOJI_RE.sub("", s)


def migrate(db, dry_run=False):
    cursor = db.cursor()

    # 1. Migrate articles (title, lead, text)
    print("Scanning 'article' table for emojis...")
    art_rows = cursor.execute("SELECT id, title, lead, text FROM article").fetchall()
    art_updated = 0
    title_updated = 0
    lead_updated = 0
    text_updated = 0

    for aid, title, lead, text in art_rows:
        new_title = strip_em(title)
        new_lead = strip_em(lead)
        new_text = strip_body(text)

        if new_title != title or new_lead != lead or new_text != text:
            art_updated += 1
            if new_title != title:
                title_updated += 1
            if new_lead != lead:
                lead_updated += 1
            if new_text != text:
                text_updated += 1

            if not dry_run:
                cursor.execute(
                    "UPDATE article SET title=?, lead=?, text=? WHERE id=?",
                    (new_title, new_lead, new_text, aid),
                )

    print(f"Articles updated: {art_updated} / {len(art_rows)}")
    print(f"  Titles: {title_updated}, Leads: {lead_updated}, Bodies: {text_updated}")

    # 2. Migrate excerpts
    print("Scanning 'excerpt' table for emojis...")
    exc_rows = cursor.execute("SELECT id, text FROM excerpt").fetchall()
    exc_updated = 0
    for eid, text in exc_rows:
        new_text = strip_em(text)
        if new_text != text:
            exc_updated += 1
            if not dry_run:
                cursor.execute("UPDATE excerpt SET text=? WHERE id=?", (new_text, eid))
    print(f"Excerpts updated: {exc_updated} / {len(exc_rows)}")

    if not dry_run:
        db.commit()
        print("Migration committed successfully.")
    else:
        print("Dry run complete; no changes committed.")

    return art_updated, exc_updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strip emojis from Argos SQLite database.")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without committing.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        migrate(conn, dry_run=args.dry_run)
    finally:
        conn.close()
