# Argos Monitor: Achieved Log

Completed items moved from `docs/roadmap.md` per project handover rules.

- **Major Regional Desks Expansion to 10+ Sources (Phase 3 Batch 3)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Poland (10 direct), Turkey (10 direct), South Korea (11 direct), India (10 direct), and Taiwan (11 direct), bringing 18 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Strategic Regional Desks Expansion to 10+ Sources (Phase 3 Batch 2)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for France (10 direct), Germany (10 direct), Japan (10 direct), Russia (10 direct), and Ukraine (10 direct), bringing 13 major global desks into full compliance with the 10-source standard.
  - Verified feed reachability with fast parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Independent Source Audit & Tier 1 Desk Expansion (Phase 3 Initial Rollout)** — **Done 2026-11-10.**
  - Created source depth auditing tool `tools/audit_sources.py` tracking direct non-aggregator vs aggregator counts across all 87 country packs.
  - Expanded and verified candidate feeds for United States (11 direct), China (10 direct), Brazil (11 direct), and United Kingdom (10 direct), joining Vietnam (27), Hungary (16), South Africa (14), and Cambodia (10) in full compliance with the 10-source standard.

- **Wire Syndication & Attribution Deduplication (Phase 2)** — **Done 2026-11-10.**
  - Wire attribution matching: added `WIRE_CREDIT_RE` and lowered `WIRE_THRESHOLD = 0.35` in `argos/normalise.py` to identify syndicated wire reprints (e.g. VNA, APS, BelTA, Reuters, AP) even when wrapped in commentary or lightly edited by local commercial newsrooms (Rule 5).
  - Lead-level shingle hashing: extended content shingling to include article leads when full text extraction is partial.
  - Added comprehensive unit tests in `tests/test_normalise.py`.

- **Media Cloud & EMM Architectural Lift (Phase 1)** — **Done 2026-11-10.**
  - Ingestion efficiency: HTTP 304 conditional GETs (`ETag`, `Last-Modified`) and exponential backoff quarantine state machine in `argos/fetch.py`, `argos/db.py`, and `argos/ingest.py`.
  - Canonical URL normalization: tracking query parameter scrubbing (`clean_url`) in `argos/textutil.py` to prevent duplicate article rows across aggregators and direct feeds.
  - EMM statistical surge detection: Poisson velocity Z-score modeling in `argos/export.py` and `tests/test_delta.py`.
  - EMM quotation extraction: attribution verb and quotation prioritization in `argos/excerpts.py` for verbatim dashboard pull-quotes.
  - Methodology synchronization: updated pipeline stage documentation in `site/about.html` per Rule 6 and Rule 7.

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
  - **Violent Events & Crisis Intelligence Hardening (Civil Unrest, UN Security, & OSINT Signals)** — **Done 2026-11-07.**
    Addressed the gap in breaking violent event reporting without incurring paid API costs or brittle scraping locks. Added high-priority `unrest_conflict` theme (`weight: 1.0`, `category: defence_security`) to `themes.yaml` and included it in the `ALWAYS` preservation set in `argos/policy.py`, ensuring political violence, armed clashes, bombings, and riots are never demoted into low-weight (0.1) local crime. Integrated official United Nations Peace & Security incident updates (`UN_PEACE`) into `argos/crisis.py` alongside USGS, GDACS, and elevated US/UK travel warnings. Expanded `argos/social.py` with global open conflict and incident monitors (Liveuamap `@liveuamap`, Insider Paper `@insiderpaper`, Reuters, AP, AFP, OSINTtechnical) dynamically matched against country desk keywords, plus curated verified regional Telegram and Bluesky handles across 13 priority desks (`vietnam`, `israel`, `iran`, `qatar`, `russia`, `georgia`, `belarus`, `myanmar`, `dr_congo`, `ethiopia`, `nigeria`, `mexico`, `venezuela`). Updated `site/about.html` and `site/app.js` documentation per Rule 6 with zero emojis.
  - **Religious & Sectarian Sensitivity Track in Conflict & Security (Multi-Confessional Lens)** — **Done 2026-11-07.**
    Enveloped religious and confessional vulnerability monitoring strictly within the `defence_security` domain. Added top-priority `sectarian_conflict` theme (`weight: 1.0`, `category: defence_security`) to `themes.yaml` and included it in the `ALWAYS` preservation set in `argos/policy.py`. Implemented sub-track navigation tabs in `site/app.js` under the Conflict & Security monitor (`#violence`) with multi-confessional filtering across Judaism (`rel_jewish`), Christianity (`rel_christian`), Islam (`rel_islam`), and Other Faiths & Sacred Sites (`rel_other`), plus overall `rel_all`, alongside insurgency and civil unrest tracks. Added broadsheet typographic stamps (`REL SENSITIVITY: TRADITION`) in story sliplines and synchronized full methodology and legend documentation in `site/about.html` and `site/index.html` per Rule 6 and Rule 7.
  - **Website Security Audit & Edge Hardening (CSP, HSTS, OPSEC Referrer Isolation, & Request Throttling)** — **Done 2026-11-09.**
    Conducted full in-depth security audit of the static site (`site/`), client runtime (`app.js`, `brief.html`), and Cloudflare Pages headers (`_headers`). Deployed strict Content Security Policy (`CSP`), `Strict-Transport-Security` (`HSTS`), `Cross-Origin-Opener-Policy`, and `Permissions-Policy`. Enforced strict outbound referrer isolation (`Referrer-Policy: no-referrer` and `rel="noopener noreferrer"` across all links) to protect analyst privacy when navigating to monitored authoritarian foreign media. Hardened `site/brief.html` with throttled sequential request batching to prevent API request storms, sanitized `site/watch.xml` feed description to prevent tracking term exposure, and synchronized `site/about.html` per Rule 6 and Rule 7 with zero emojis.
  - **Domain Configuration (argosmonitor.uk) & Production Search Engine Optimization (SEO)** — **Done 2026-11-09.**
    Configured custom root apex domain and `www` host records for `argosmonitor.uk` on Cloudflare edge. Configured production sitemap (`site/sitemap.xml`) with canonical URL hierarchies, Open Graph / Twitter Card social metadata, robots directives (`site/robots.txt`), and search engine indexing readiness across all 87 country desks.
  - **About Page Navigation & Typographic Layout Harmonization (Rule 6, Rule 7)** — **Done 2026-11-09.**
    Restored and unified the primary global top navigation bar across `site/about.html` matching the main monitor (`Overview`, `Country Brief`, `Joint & Multilateral`, `Alerts`, `Disasters`, `Conflict & Security`, `About`), with active tab indicator and dynamic alert counts. Removed the horizontal section subnav bar and associated CSS. Restructured badge definition rows in the methodology text with clean typographic alignment and zero emojis.
    Configured production SEO infrastructure for registered custom domain `argosmonitor.uk`: generated `site/robots.txt` and `site/sitemap.xml` with priority hierarchy; created 1200x630 broadsheet social preview banner (`site/assets/og-preview.png`) complying with zero-emoji standards; integrated Open Graph, Twitter Card, canonical links, and Schema.org JSON-LD structured data (`NewsMediaOrganization`, `WebSite`, `AboutPage`) across `index.html`, `about.html`, `brief.html`, and `sources.html`; synchronized RSS channel metadata in `argos/watch.py`, `README.md`, and `CITATION.cff`; updated edge cache headers in `site/_headers`.
