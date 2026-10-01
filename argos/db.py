import sqlite3
from .config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS source (
  id TEXT PRIMARY KEY, name TEXT, homepage TEXT, language TEXT, scope TEXT, kind TEXT,
  governing_body TEXT, state_affiliated INTEGER, reprints_vna INTEGER, notes TEXT);
CREATE TABLE IF NOT EXISTS feed (
  id INTEGER PRIMARY KEY, source_id TEXT REFERENCES source(id), url TEXT UNIQUE,
  section_label TEXT, category_hint TEXT, active INTEGER, last_ok_at TEXT, last_error TEXT);
CREATE TABLE IF NOT EXISTS article (
  id INTEGER PRIMARY KEY, source_id TEXT REFERENCES source(id), feed_id INTEGER,
  url TEXT UNIQUE, title TEXT, lead TEXT, text TEXT, language TEXT,
  published_at TEXT, fetched_at TEXT, extract_status TEXT,
  content_hash TEXT, syndicated_of INTEGER, vn_relevant INTEGER);
CREATE TABLE IF NOT EXISTS embedding (article_id INTEGER PRIMARY KEY REFERENCES article(id), vec BLOB);
CREATE TABLE IF NOT EXISTS story (
  id INTEGER PRIMARY KEY, window_days INTEGER, window_start TEXT, window_end TEXT, category TEXT, score REAL,
  first_seen TEXT, last_seen TEXT, representative_article_id INTEGER, policy REAL, themes TEXT);
CREATE TABLE IF NOT EXISTS story_article (story_id INTEGER REFERENCES story(id), article_id INTEGER REFERENCES article(id),
  PRIMARY KEY (story_id, article_id));
CREATE TABLE IF NOT EXISTS translation (article_id INTEGER PRIMARY KEY REFERENCES article(id), text_en TEXT, model TEXT);
CREATE TABLE IF NOT EXISTS excerpt (
  id INTEGER PRIMARY KEY, story_id INTEGER REFERENCES story(id), article_id INTEGER REFERENCES article(id),
  text TEXT, char_start INTEGER, char_end INTEGER);
CREATE INDEX IF NOT EXISTS article_source ON article(source_id);
CREATE INDEX IF NOT EXISTS article_status ON article(extract_status);
"""


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cols = {r[1] for r in db.execute("PRAGMA table_info(story)")}
    if cols and "window_days" not in cols:      # stories are derived data: rebuilt by the cluster stage
        db.executescript("DROP TABLE IF EXISTS excerpt; DROP TABLE IF EXISTS story_article; DROP TABLE IF EXISTS story;")
    db.executescript(SCHEMA)
    story_cols = {r[1] for r in db.execute("PRAGMA table_info(story)")}
    for col, kind in (("policy", "REAL"), ("themes", "TEXT")):
        if col not in story_cols:
            db.execute(f"ALTER TABLE story ADD COLUMN {col} {kind}")   # columns added after the first databases existed
    if "vn_relevant" not in {r[1] for r in db.execute("PRAGMA table_info(article)")}:
        db.execute("ALTER TABLE article ADD COLUMN vn_relevant INTEGER")  # database created before this column existed
    return db
