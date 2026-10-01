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
  content_hash TEXT, syndicated_of INTEGER, relevant INTEGER, country TEXT);
CREATE TABLE IF NOT EXISTS embedding (article_id INTEGER PRIMARY KEY REFERENCES article(id), vec BLOB);
CREATE TABLE IF NOT EXISTS story (
  id INTEGER PRIMARY KEY, country TEXT, window_days INTEGER, window_start TEXT, window_end TEXT, category TEXT, score REAL,
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


def _columns(db, table):
    return {r[1] for r in db.execute(f"PRAGMA table_info({table})")}


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cols = _columns(db, "story")
    if cols and "window_days" not in cols:      # stories are derived data: rebuilt by the cluster stage
        db.executescript("DROP TABLE IF EXISTS excerpt; DROP TABLE IF EXISTS story_article; DROP TABLE IF EXISTS story;")
    db.executescript(SCHEMA)

    # Databases created before a column existed get it added.
    for table, col, kind in (("story", "policy", "REAL"), ("story", "themes", "TEXT"), ("story", "country", "TEXT"),
                             ("article", "country", "TEXT")):
        if col not in _columns(db, table):
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    art = _columns(db, "article")
    if "vn_relevant" in art and "relevant" not in art:
        db.execute("ALTER TABLE article RENAME COLUMN vn_relevant TO relevant")
    elif "relevant" not in art:
        db.execute("ALTER TABLE article ADD COLUMN relevant INTEGER")
    db.execute("UPDATE article SET country='vietnam' WHERE country IS NULL")     # everything collected before packs was Vietnam
    db.execute("UPDATE source SET scope='abroad_local' WHERE scope='abroad_vi'")
    db.commit()
    return db
