# Argos Monitor: Achieved Log

Completed items moved from `docs/roadmap.md` per project handover rules.

- **Phase 1: Vietnam MVP (no LLM, 7-day window)** — **Done 2026-09-30.**
  - Verified sources in `sources.yaml`.
  - Ingestion, full-text extraction via trafilatura, NFC normalisation, syndication detection.
  - Multilingual embedding and DBSCAN clustering.
  - Topic classification across 6 categories.
  - Broadsheet static site generation (`site/index.html`, vanilla JS, zero frameworks).
  - Automated deployment workflow via GitHub Actions to Cloudflare Pages edge.

- **Phase 2 Items:**
  - **A second country (Hungary, D15) & Global Expansion** — **Done 2026-11-04.**
    Expanded pipeline and registry to 87 country packs across 16 geopolitical regions (Tiers 1, 2, and 3), with 100% feed reachability and automated fallbacks.
  - **Source political alignment, editorial leaning, and perspective analysis (D22)** — **Done 2026-11-04.**
    Calibrated bias, affiliation, and factuality tags for all monitored publications; added state-dominated narrative telemetry.
  - **Conflict & Security sensor and official advisory model (D23)** — **Done 2026-11-04.**
    Retired heuristic regex violence tagging; anchored crisis monitoring in verified external sensor networks (GDACS, USGS, NASA EONET) and statutory foreign ministry advisories (US State Dept, UK FCDO, Crisis Group).
  - **Uncapped story export & UI expansion** — **Done 2026-11-05.**
    Removed hardcoded 12-story limitation; exported complete story clusters per country window; added "Show all" / "Open all" drawer navigation and top-100 brief support.
  - **"What changed?" delta comparisons between windows (D24, D25, docs/delta_spec.md)** — **Done 2026-11-05.**
    Deterministic two-window partitioning ($T$ vs $T_{-1}$), story movement states (`[NEW]`, `[SURGE +ΔN]`, `[COOLING]`), international/diaspora scope escalation (`[INTL PICKUP]`, `[DIASPORA PICKUP]`), state media narrative drift (`[STATE SURGE]`), and Macro Agenda Movement Bar (`site/app.js`, `site/style.css`, `site/about.html`) with zero emojis.
  - **Bilateral delta cross-comparisons in Multilateral Affairs** — **Done 2026-11-05.**
    Scoreboard calculating bilateral news cycle momentum multipliers, net article growth (&Delta;N), breakout badges, and lead policy domain concentration in the Joint & Multilateral Affairs monitor.
  - **Basic Social Watch from accessible sources (Telegram, Bluesky, Reddit, Google Trends)** — **Done 2026-11-05.**
    Ingests open Telegram channel web previews (t.me/s/) and open AT Protocol Bluesky feeds without API keys or authentication, with NFC diacritic normalisation (Rule 3) and zero-emoji scrubbing (Rule 7), displaying unverified auxiliary signals in the desk sidebar.
  - **Searchable Country Combobox with live diacritic-insensitive filtering** — **Done 2026-11-05.**
    Replaced native `<select id="country">` scrolling bottleneck with accessible, zero-dependency Combobox (`#country-search`) supporting instant diacritic-folded filtering (`fold()`) across country names, pack IDs, region names (e.g. "balkans"), and pack alias keywords (`mentions`), with keyboard navigation (`ArrowDown`, `ArrowUp`, `Enter`, `Escape`), click-outside dismissal, regional grouping, and zero emojis.
  - **Full 87-Country Edge Deployment & Ingestion Pipeline Hardening** — **Done 2026-11-05.**
    Ingested, clustered, and deployed all 87 country desks to Cloudflare Pages edge (`site/data/index.json`); hardened `argos/cluster.py` to handle single-article windows without crashing `AgglomerativeClustering`; protected `run.py` pipeline against auxiliary stage faults (`reddit`, `social`); verified live availability of Iran (194 stories), Ukraine (316 stories), and all global desks with zero emojis.
  - **Offline Headline Translation via MarianMT Sequence-to-Sequence Models (Roadmap Item 2)** — **Done 2026-11-05.**
    Implemented CPU-friendly, zero-LLM offline headline translation in `argos/translate.py` using language-specific Marian models (`Helsinki-NLP/opus-mt-*`), SQLite translation cache, and geopolitical entity alignment glossaries. Exported `en_title` in story payloads (`argos/export.py`) with instant broadsheet display and `[Show original]` toggle in `site/app.js`, fully automated in `.github/workflows/daily.yml`.
  - **Typographic Badge & Stamp Polish (Clean Broadsheet Design)** — **Done 2026-11-05.**
    Stripped redundant literal brackets from all delta movement stamps (`NEW`, `NEW EMERGENCE`, `SURGE +ΔN`, `COOLING`, `INTL PICKUP`, `DIASPORA PICKUP`, `STATE SURGE`) across story sliplines, bilateral momentum scoreboards, and the About page methodology, letting clean CSS stamp borders define badge boundaries.
  - **Comprehensive Methodology & Architecture Documentation Sync (Rule 6)** — **Done 2026-11-05.**
    Expanded `site/about.html` with detailed, authoritative methodology chapters and subnav quick-links: Verbatim Evidence & Substring Assertion Engine, Wire De-duplication & Independent Corroboration, Offline MarianMT Machine Translation & Geopolitical Glossaries, Foreign-Office Policy Relevance & Ranking Formulation, Auxiliary Social Signals & Strict Evidentiary Segregation, and Zero-Cost / Zero-Telemetry Edge Architecture.
  - **Public Repository Description & Portfolio README Modernization** — **Done 2026-11-05.**
    Synchronized GitHub repository description via authenticated REST API with the 87-country, 760-feed architecture, MarianMT offline translation, and verified zero-LLM evidence standards. Updated `README.md` pipeline architecture diagram and stage table from 10 to 11 stages (incorporating `argos/translate.py` and multi-signal export).
  - **Daily Digest Pipeline Fix & ONNX Embedder Resilience** — **Done 2026-11-07.**
    Diagnosed daily digest pipeline failure in GitHub Actions (`Collect, analyse and export` stage). Identified that newly onboarded country packs with custom themes lacking `describe` fields passed empty arrays to `Embedder.encode([])`, triggering an ONNX Runtime 1D vs 2D rank mismatch on `token_type_ids`. Added empty-input guard in `argos/embed.py`, fallback to `t['label']` in `argos/policy.py` and `argos/reddit.py`, country-level story existence check to skip zero-story desks in policy scoring, and batch chunking for translation candidate lookups in `argos/translate.py`. Verified with targeted unit tests.
  - **Standing Rule 8: Priority Coverage for Elections & Ballots** — **Done 2026-11-07.**
    Codified non-negotiable Rule 8 in `CLAUDE.md`: national, presidential, parliamentary, and local elections, referendums, and ballot outcomes receive top policy weighting (1.0) and priority placement at the top of diplomatic news briefs (`site/brief.html`) and desk overviews across all countries. Added top-level `elections` theme to `themes.yaml`, included `elections` in `ALWAYS` theme preservation list in `argos/policy.py`, implemented deterministic election priority scoring boost in `argos/rank.py`, added `isElectionStory` dispatch sorting and `ELECTION PRIORITY` typographic stamp in `site/brief.html`, and updated full methodology documentation in `site/about.html` per Rule 6 with zero emojis.
