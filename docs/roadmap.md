# Roadmap

Each step has a check that shows it is done. Work in order.

## Phase 1: Vietnam MVP (no LLM, 7-day window)

1. **Verify sources.** Check every candidate in [sources.md](sources.md): is it alive in 2026, do the RSS/section feeds work, and fill in the metadata. Write `sources.yaml`.
   → Done when: a script fetches every feed in `sources.yaml` and reports OK with a non-zero item count for each.
2. **Project setup.** `requirements.txt`, check package support on Python 3.14, create `C:\ArgosData`, write a plain-language "how to run" section in the README.
   → Done when: the user can run one command that prints "setup OK".
3. **Ingest + extract + normalise.** RSS and GDELT into SQLite; full text via trafilatura; NFC; syndication detection.
   → Done when: one run stores more than 1,000 articles from domestic, abroad_vi and international sources; re-running adds no duplicates.
4. **Embed + cluster.**
   → Done when: a hand-checked sample of about 30 stories is mostly correct: same event grouped together, different events kept apart, and Vietnamese and English coverage of one event merged.
5. **Classify + rank.**
   → Done when: the top 10 stories look sensible to the user; each category has content.
6. **Export data and build the site (D12). Built 2026-09-30; see the notes below.** The pipeline writes one data file per country and period (24h, 7d) with every story, its category, coverage breakdown, evidence label and verified quoted excerpts. A static page (`site/index.html`, vanilla JS, no framework) has a country dropdown, a time selector, a topic selector and a Research button that shows the matching stories. It works on phone and laptop. Use `/impeccable` for the design.
   → Done when: every excerpt on the page matches its stored article text exactly (automated check), the three selectors filter the stories correctly, and the page opens from a local folder.
7. **Schedule in the cloud (D13).** GitHub Actions runs the pipeline once a day (04:00 Vietnam time) and publishes the site to Cloudflare Pages.
   → Done when: the cloud probe shows most outlets reachable, and a scheduled run publishes a fresh site before 07:00 without help.

## Phase 2: later (not yet planned in detail)
- 24h / 30d windows and "what changed?" comparison with the previous period
- Optional LLM layer for the top stories, with the verbatim-quote check
- Offline headline translation (`opus-mt-vi-en`)
- A second country (Poland or Ukraine)
- Basic Social Watch from accessible sources (YouTube, Google Trends; Telegram and Bluesky for other countries)
- Saved watches and a morning brief
