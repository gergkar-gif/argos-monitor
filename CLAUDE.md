# Argos Monitor

A multilingual, evidence-first news monitoring dashboard. **First target: Vietnam.**
The user picks a country and a period. The app collects news, groups articles about the same event into stories, sorts the stories by subject, and shows where the coverage comes from (domestic, Vietnamese-language outside the country, international). Every sentence it shows can be traced to a source article.

The project has not been built yet. Read these before doing any work:
- [docs/decisions.md](docs/decisions.md): decisions already made and why. Don't reopen them without asking.
- [docs/architecture.md](docs/architecture.md): pipeline, data model, folder layout
- [docs/sources.md](docs/sources.md): source registry schema and candidate sources (not yet verified)
- [docs/roadmap.md](docs/roadmap.md): what to build next
- [docs/brief.md](docs/brief.md): the original product brief (long-term vision, not MVP scope)

## Non-negotiable rules
1. **No source, no statement.** Everything shown to the user is either an article's own headline or text quoted directly from a stored article, linked to its `article_id`. The app never writes fact sentences of its own.
2. **The core pipeline uses no LLM.** It runs free, offline apart from fetching, on the user's PC. An LLM layer, if one is added later, is optional. Any claim it produces must come with a verbatim quote that code checks by string match against the stored article text. If the quote isn't found, the claim is dropped.
3. **Unicode NFC normalisation** is applied to all Vietnamese text as soon as it is ingested, before hashing, embedding or quote matching. Vietnamese sites mix composed and decomposed diacritics.
4. **The original-language article is the authoritative source.** A translation is never evidence. Translation is left to the browser.
5. **Don't count syndicated copies as separate sources.** Many domestic outlets reprint VNA (Vietnam News Agency) copy. The story page must show *independent* source counts.

## Environment
- Windows 11, 8 GB RAM, Python 3.14. Everything must run on CPU and stay light on memory.
- **The project folder is on Google Drive. Never put the SQLite database or caches inside it**, because Drive sync corrupts or locks database files. Data goes in `ARGOS_DATA_DIR` (default `C:\ArgosData`).
- The user doesn't write code. Explain how to run things in plain steps, one command at a time.
- The `impeccable` design skill is installed in `.claude/skills/`. Use it for dashboard/UI work (`/impeccable init` once there is a UI to design).

## Conventions
- Python, standard library first. Add a dependency only when it clearly earns its place, and list it in `requirements.txt`.
- The output is a static website in `site/` (plain HTML/CSS/vanilla JS, no server, no JS framework) fed by JSON files the pipeline writes. See D12.
- Simple over clever. This is a prototype for one user.
