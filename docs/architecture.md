# Architecture (MVP)

## Pipeline

```
sources.yaml ─▶ ingest ─▶ extract ─▶ normalise ─▶ embed ─▶ cluster ─▶ classify ─▶ rank ─▶ render
  (registry)    (RSS,     (full      (NFC,        (local    (stories,  (section    (score)  (dashboard.html)
                 GDELT)    text)      dedupe)      model)    syndication) feed/emb.)
```

`python run.py` runs every stage in order. Each stage reads from and writes to SQLite, so a stage can be re-run on its own.

| Stage | What it does | Tooling (planned) |
|---|---|---|
| ingest | Fetch each RSS feed in the registry, plus GDELT DOC API queries for international coverage of Vietnam. Store new article URLs with title, lead, publish time and feed section. | `feedparser`, `httpx` |
| extract | Fetch each article page and extract its main text. Be polite: rate limit, set a user agent, respect robots.txt. | `trafilatura` |
| normalise | NFC-normalise all text, strip whitespace, compute a content hash. Near-duplicate text from different outlets is marked as syndicated (e.g. VNA reprints). | stdlib `unicodedata`, hashing / shingling |
| embed | Embed `title + lead` of each article with a small multilingual model on CPU. | `multilingual-e5-small` (via `sentence-transformers`, or an ONNX runtime to avoid installing torch; decide at setup) |
| cluster | Group articles into stories: cosine similarity + a publish-time window, agglomerative clustering. Articles in different languages about the same event should end up together. | `scikit-learn` |
| classify | Story category = majority of its articles' section-feed categories. Fall back to embedding similarity to category descriptions. | own code |
| rank | Score = independent sources (syndicated copies count once) + coverage growth + spread across domestic / abroad_vi / international. The top 5–10 form the executive overview. | own code |
| render | Write a static HTML dashboard: categories → story cards → coverage breakdown → list of quoted sentences and source links. | `jinja2` (or stdlib string templates) |

## Data model (SQLite)

```
source        id, name, homepage, language, scope (domestic|abroad_vi|international),
              kind (media|official|wire), governing_body, state_affiliated (bool),
              reprints_vna (bool), notes

feed          id, source_id, url, section_label, category_hint, active, last_ok_at, last_error

article       id, source_id, feed_id, url (unique), title, lead, text, language,
              published_at, fetched_at, content_hash, syndicated_of (article_id|null)

story         id, window_start, window_end, category, score, first_seen, last_seen,
              representative_article_id

story_article story_id, article_id

excerpt       id, story_id, article_id, text, char_start, char_end
              -- a sentence shown on the dashboard. It must equal article.text[char_start:char_end].
              -- This is the audit trail for "no source, no statement".
```

Evidence label for a story (D3): `OFFICIAL` if any member article comes from a source with `kind=official`, otherwise `REPORTED`.

## Folder layout (planned)

```
Argos Monitor/            (on Google Drive: code and docs only)
  CLAUDE.md
  docs/
  sources.yaml            source + feed registry (edited by hand)
  requirements.txt
  run.py                  runs the whole pipeline
  argos/                  one module per stage
  templates/dashboard.html.j2

C:\ArgosData\             (outside Drive, set by ARGOS_DATA_DIR)
  argos.db
  models/                 downloaded embedding model cache
  out/dashboard.html
```

## Scale and resources
- About 20–30 outlets means roughly 1,500–3,000 articles a day, so about 15–20k in a 7-day window.
- Embedding title and lead with e5-small on CPU should take minutes, not hours. It fits in 8 GB RAM.
- **Python 3.14 risk:** check that `torch` / `onnxruntime` / `scikit-learn` publish wheels for 3.14 before committing to them. If they don't, install Python 3.12 alongside.

## Legal and ethics
Full article text is stored locally, only for clustering and quote checking. The dashboard shows headlines, short quoted excerpts and links, and never republishes whole articles.
