# System Architecture

## 11-Stage Deterministic Pipeline

```
countries/<id>/*.yaml ─▶ ingest ─▶ normalise ─▶ relevance ─▶ embed ─▶ cluster ─▶ classify ─▶ policy ─▶ rank ─▶ extract ─▶ excerpts ─▶ verify ─▶ translate ─▶ export
```

`python run.py` executes the full pipeline in order, reading from and writing to SQLite (`ARGOS_DATA_DIR/argos.db`) so individual stages can be re-run independently. Automated production builds run every 12 hours (09:17 and 21:17 UTC) via GitHub Actions and publish static bundles to Cloudflare Pages.

| Stage | Module | Description |
| :--- | :--- | :--- |
| **01 · Ingest** | `argos/ingest.py` | Polls 1,672 RSS/Atom and Google News aggregator feeds across 89 country desks (`domestic`, `abroad_local`, `international`) and reconciles source ratings (`argos/ratings.py`). |
| **02 · Normalise** | `argos/normalise.py` | Applies Unicode NFC normalisation, strips control characters and emojis, and computes content hashes for syndication detection. |
| **03 · Relevance** | `argos/relevance.py` | Enforces URL section filters (`url_sections`) and country-mention gates on multi-country and international feeds. |
| **04 · Embed** | `argos/embed.py` | Encodes `title + lead` into 384-dimensional vectors on CPU via ONNX Runtime (`intfloat/multilingual-e5-small`). |
| **05 · Cluster** | `argos/cluster.py` | Two-pass agglomerative cosine clustering within active time windows (24h, 7d), collapsing syndicated wire reprints ($\ge 0.95$ cosine similarity) so independent outlet counts remain accurate. |
| **06 · Classify** | `argos/classify.py` | Assigns stories to 6 policy domains (`Politics & Governance`, `Diplomacy & Foreign Policy`, `Economy & Trade`, `Defence & Security`, `Society & Rights`, `Environment & Energy`) using feed category hints and bilingual anchor embeddings. |
| **07 · Policy & Rank** | `argos/policy.py`, `argos/rank.py` | Scores stories against shared and country-specific geopolitical fault lines (`themes.yaml`), weighting independent outlet diversity, scope spread, and election priority. |
| **08 · Extract** | `argos/extract.py` | Round-robin full-text extraction via `trafilatura` for active clustered stories (`ARGOS_EXTRACT_STORY_ONLY=1`), respecting per-domain rate limits. |
| **09 · Excerpts & Verify** | `argos/excerpts.py`, `argos/verify.py` | Extracts representative sentences and verifies every excerpt by exact character-offset substring match (`article.text[char_start:char_end]`). Unverified quotes are dropped. |
| **10 · Translate** | `argos/translate.py` | Offline CPU sequence-to-sequence headline translation via MarianMT (`Helsinki-NLP/opus-mt-*`) with domain entity glossaries, cached in SQLite while preserving the original-language headline as authoritative. |
| **11 · Signals & Export** | `argos/crisis.py`, `argos/trends.py`, `argos/social.py`, `argos/reddit.py`, `argos/export.py` | Integrates GDELT 2.0 conflict streams, GDACS/USGS/NASA EONET hazard feeds, US State Dept & UK FCDO advisories, UN/ICG/HRW field reports, auxiliary Telegram/Bluesky/Reddit signals, and period-over-period delta metrics (`docs/delta_spec.md`) into static JSON/JS bundles in `site/data/`. |

## Core Data Model (SQLite)

```
source        id, country, name, homepage, language, scope (domestic|abroad_local|international),
              kind (media|official|wire), governing_body, state_affiliated (bool),
              reprints_vna (bool), alignment, bias, factuality, notes

feed          id, source_id, url, section_label, category_hint, active, last_ok_at, last_error

article       id, country, source_id, feed_id, url (unique), title, lead, text, language,
              published_at, fetched_at, content_hash, syndicated_of (article_id|null)

story         id, country, window_start, window_end, category, score, policy_score,
              first_seen, last_seen, representative_article_id

story_article story_id, article_id

excerpt       id, story_id, article_id, text, char_start, char_end
              -- Must equal article.text[char_start:char_end] ("no source, no statement").
```

## Repository Layout

```
argos-monitor/
  argos/                  11-stage pipeline modules, source ratings, and signal collectors
  countries/<id>/         89 declarative country packs (pack.yaml, sources.yaml, themes.yaml)
  docs/                   Architecture, source registry schema, and delta specification
  site/                   Static broadsheet frontend (HTML, CSS, vanilla JS, precomputed data/)
  tests/                  Unit and invariant guard suites
  tools/                  Feed verification and audit utilities
  themes.yaml             Global baseline policy themes and weights
  run.py                  CLI pipeline entrypoint
```

## Legal & Evidentiary Standards
Full article text is stored exclusively in the local/ephemeral SQLite database for clustering and exact substring quote verification. The published static interface displays only headlines, short verified excerpts, source metadata, and direct outbound links (`rel="noopener noreferrer"`) to the original publishers.
