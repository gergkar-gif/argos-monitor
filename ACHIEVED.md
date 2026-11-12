# Argos Monitor: Achieved Log

Completed items moved from `docs/roadmap.md` per project handover rules.

- **Pipeline Throughput Optimization & Baltic States Native Feed Expansion** — **Done 2026-11-12.**
  - Resolved root cause of stale story clusters on GitHub Actions: unconstrained `extract` stage previously attempted full-text HTML extraction on 8,000+ pending articles across 1,360+ feeds before clustering, causing GitHub Actions workflows to exceed runner time limits (150 minutes) and stall before `cluster` or `export` could run.
  - Reordered pipeline stages in `run.py` and `.github/workflows/daily.yml` to cluster and rank stories first via lightweight ONNX title/lead embeddings (~2 minutes), followed by targeted article text extraction only for active story candidates (`ARGOS_EXTRACT_STORY_ONLY=1`, `ARGOS_EXTRACT_LIMIT=400`), reducing full pipeline execution time to ~10–12 minutes.
  - Expanded the Baltic States desk (`countries/baltics/sources.yaml` and `pack.yaml`) with native Estonian, Latvian, and Lithuanian feeds: added Estonian Public Broadcasting (`ERR Uudised` in Estonian via `err.ee/rss`), Postimees (`postimees.ee/rss`), Google News Estonia (`hl=et`), Lithuanian Public Broadcaster (`LRT Naujienos` in Lithuanian via `lrt.lt`), and Google News Latvia/Lithuania native aggregators. Updated `mention` patterns to recognize Estonian, Latvian, and Lithuanian native country names and leaders (`eesti`, `latvija`, `lietuva`, `riigikogu`, `saeima`, `seimas`). Total feeds increased to 1,373 across 1,195 catalogued sources.
  - Hardened `site/app.js` and `site/index.html`: synchronized period state so 7-day fallback files never display under a "last 24 hours" header, added explicit "No stories found in this time period" empty states instead of blank views, and bumped script version to `app.js?v=3.7` for instant cache busting.

- **Global Native-Language Aggregator Standardization Across All 87 Desks** — **Done 2026-11-12.**
  - Conducted global audit of all 87 country packs for aggregator presence and primary language coverage. Identified 36 non-English desks with English-only aggregator queries that failed to capture daily domestic news cycles when direct feeds were quiet or bot-restricted.
  - Implemented automated migration tool (`tools/upgrade_aggregators.py`) and equipped all 36 deficit packs with high-yield native-language Google News aggregator streams (Arabic across MENA, French in Morocco/Belgium, Spanish across Latin America, Portuguese in Brazil/Portugal, German, Russian, Turkish, Vietnamese, Chinese, Hebrew, etc.).
  - Brought total active monitored feeds across all 87 country desks to 1,365 feeds across 1,189 catalogued sources (0 deficit packs remaining; 100% native-language aggregator coverage globally).
  - Synchronized documentation, pipeline diagrams, and telemetric source counts in `README.md` and `site/about.html` per Rule 6 and Rule 7 with zero emojis.

- **Algeria Feed Ingestion & Date Parser Resilience** — **Done 2026-11-12.**
  - Identified why Algeria previously had 0 stories in 24 hours: state agency `aps.dz` deprecated public open RSS feeds (`https://www.aps.dz/algerie/feed`), direct feeds were constrained, and the single aggregator feed was restricted to an English-only energy subset.
  - Added French, Arabic, and official APS Google News aggregators (`gnews_algeria_fr`, `gnews_algeria_ar`, `gnews_algeria_aps`) in `countries/algeria/sources.yaml`, guaranteeing continuous daily coverage of Algerian domestic governance, economics, and foreign policy without relying on defunct direct endpoints.
  - Enhanced `parse_date` in `argos/textutil.py` with ISO 8601 fallback parsing, preventing feed entries with standard ISO timestamps from falling back to NULL publication dates.

- **Window Slicing & Period Fallback Integrity Fix** — **Done 2026-11-12.**
  - Fixed client-side period label deception in `site/app.js`: when a requested period snapshot (such as `24h`) was missing, the client previously loaded the `7d` dataset while leaving the period header and dropdown claiming "last 24 hours", causing 2-day-old news to appear under a 24-hour banner.
  - Hardened `site/app.js` and `site/brief.html`: now dynamically limits period selection to available country periods (`c.periods`), synchronizes the dropdown/header to the actual data period (`d.period`), and displays a clear disclaimer banner whenever fallback to 7-day coverage occurs.
  - Updated `argos/export.py` to always export clean, well-formed 24-hour JSON bundles (`{cid}-24h.json`) for all packs even when zero stories occurred in the 24-hour window, truthfully displaying "0 stories found" rather than triggering missing-file fallbacks.

- **Workflow Schedule Frequency Optimization & Quota Protection** — **Done 2026-11-12.**
  - Reverted automated pipeline schedule in `.github/workflows/daily.yml` from every 3 hours to once daily at 21:17 UTC (04:17 Indochina Time / 22:17 CET).
  - Preserves GitHub Actions monthly runner quota (2,000 minutes) across all 87 desks (~1,000 feeds) while ensuring daily morning briefs are updated and ready before 07:00 local time.
  - Updated documentation, architecture diagrams, and pipeline telemetry in `README.md`, `docs/decisions.md` (D28), and `site/about.html` per Rule 6 and Rule 7 with zero emojis.

- **Searchable Country Combobox Standardisation Across Site** — **Done 2026-11-10.**
  - Standardised the Country Brief searchable combobox component (`combobox-wrap`, keyboard arrow/enter navigation, typeahead filtering across country names, IDs, regions, and mention aliases) across all site sections: `site/index.html`, `site/brief.html`, and `site/about.html`.
  - In `site/brief.html`, replaced native `<select id="b-country">` with full searchable combobox component, syncing instant URL hash routing, region groupings, and diplomatic dispatch generation.
  - In `site/about.html`, upgraded the Source Directory filter form with the searchable country combobox with "All countries" global option and regional groupings.
  - Preserved no-dependency vanilla JavaScript and CSS broadsheet design across all views.

- **Crisis Watch & Real-Time Violence Stream Upgrade** — **Done 2026-11-10.**
  - Integrated GDELT 2.0 real-time 15-minute CAMEO violence event stream (`_gdelt_events` and `ingest_gdelt_articles` in `argos/crisis.py` covering CAMEO codes 18 Assault/Bombing, 19 Armed Clash/Strike, 20 Mass Violence, 145/175 Violent Riot/Repression) with verbatim HTML `<title>`, lead, and full-text extraction via Trafilatura (Rule 1 compliant) plus optional ACLED API support (`_acled_events`).
  - Ingested verified GDELT 2.0 conflict URLs directly into the SQLite `article` and `source` tables during both `ingest` and `crisis` stages, preserving relevance (`argos/relevance.py`) so GDELT conflict articles embed, extract verified quotes, and cluster with domestic desk stories (`story_article`).
  - Expanded open field conflict and humanitarian monitors across all 87 desks (`Human Rights Watch`: 43 alerts, `Long War Journal`: 57 alerts, `MSF Crisis Update`: 10 alerts, `Crisis Group`: 10 alerts) with full regional constituent country and sub-national conflict-zone matching (`REGIONAL_COUNTRIES` + `mention`).
  - Fixed US State Department travel advisory date parsing (`%a, %d %b %Y`), eliminating all 53 undated (`null` date) advisories and capping repetitive green GDACS notifications.
  - Added kinetic conflict track classification (`Armed Clash & Strike`, `Insurgency & Terror`, `Civil Unrest & Crackdown`) in `argos/export.py` and `site/app.js`, filtering routine non-violent defence diplomacy out of Crisis Watch and updating `site/about.html` (Rule 6).

- **Full article extraction and quote verification for newly active story feeds** — **Done 2026-11-10.**
  - Prioritized extraction of full article bodies for all pending articles attached to active story clusters (`story_article`), enabling `ARGOS_EXTRACT_STORY_ONLY` and `ARGOS_EXTRACT_LIMIT` controls.
  - Successfully extracted 311 active story article bodies across newly expanded desks (Jordan, Sri Lanka, Laos, Ukraine, Baltics).
  - Executed end-to-end extraction, normalisation, quote excerpting, and audit verification: generated 415 verbatim quote excerpts across 792 scored stories, with 415/415 excerpts verified via 100% exact character-for-character matching against stored article text (`verify: 415/415`).
  - Exported updated broadsheet data to `site/data/` (including 117 quote-verified stories for Jordan and 99 quote-verified stories for Sri Lanka).

- **Independent source expansion across all country desks (Phase 3)** — **Done 2026-11-10.**
  - Completed expansion of the final 4 deficit packs: Bangladesh (10 direct), Sri Lanka (11 direct), Laos (10 direct), and North Korea (11 direct).
  - All 87 country packs in the global registry now meet or exceed the standard of >= 10 independent direct non-aggregator sources (0 deficit packs remaining, 100% compliant across all 87 desks).
  - Validated with `tools/audit_sources.py --min 10 --fail-under` and full test suite execution.

- **Levantine & Gulf Desks Expansion to 10+ Sources (Phase 3 Batch 16)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Jordan (11 direct), Qatar (11 direct), Saudi Arabia (10 direct), Lebanon (12 direct), and Syria (12 direct), bringing 83 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe across all newly integrated publications.

- **Gulf, Central African & Middle Eastern Desks Expansion to 10+ Sources (Phase 3 Batch 15)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for United Arab Emirates (10 direct), DR Congo (11 direct), Iraq (10 direct), Iran (10 direct), and Egypt (10 direct), bringing 78 major global and regional desks into full compliance with the 10-source standard.
  - Converted DR Congo `actualite_cd` to direct RSS and integrated verified economic, mineral, and investigative feeds.
  - Verified feed reachability with parallel probe across all newly integrated publications.

- **Nordic, Caucasus, Levant & Maghreb Desks Expansion to 10+ Sources (Phase 3 Batch 14)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Denmark (11 direct), Georgia (11 direct), Israel (10 direct), Algeria (10 direct), and Morocco (10 direct), bringing 73 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe across all newly integrated publications.

- **Central Asian, Balkan, West African & Andean Desks Expansion to 10+ Sources (Phase 3 Batch 13)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Uzbekistan (10 direct), West Africa (10 direct), Kyrgyzstan (10 direct), Kosovo (10 direct), and Ecuador (10 direct), bringing 68 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe across all newly integrated publications.

- **Chilean, Kenyan, Malaysian, Ethiopian & Pacific Desks Expansion to 10+ Sources (Phase 3 Batch 12)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Chile (10 direct), Kenya (10 direct), Malaysia (10 direct), Ethiopia (10 direct), and Pacific Islands (10 direct), bringing 63 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Balkan, Moldovan, Baltic, Caribbean & East African Desks Expansion to 10+ Sources (Phase 3 Batch 11)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Bosnia (10 direct), Moldova (10 direct), Baltics (10 direct), Caribbean (11 direct), and East Africa (10 direct), bringing 58 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Caucasus, Central Asian & Central American Desks Expansion to 10+ Sources (Phase 3 Batch 10)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Kazakhstan (10 direct), Belarus (10 direct), Azerbaijan (10 direct), Armenia (10 direct), and Central America (11 direct), bringing 53 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Alpine, Balkan & South Asian Desks Expansion to 10+ Sources (Phase 3 Batch 9)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Pakistan (10 direct), Romania (10 direct), Greece (10 direct), Austria (10 direct), and Switzerland (10 direct), bringing 48 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Latin American Desks Expansion to 10+ Sources (Phase 3 Batch 8)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Argentina (10 direct), Venezuela (11 direct), Colombia (11 direct), Peru (10 direct), and Mexico (10 direct), bringing 43 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Western Europe & Nordic Expansion to 10+ Sources (Phase 3 Batch 7)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Netherlands (10 direct), Belgium (11 direct), Portugal (11 direct), Ireland (12 direct), and Sweden (11 direct), bringing 38 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Commonwealth, Nordic & African Desks Expansion to 10+ Sources (Phase 3 Batch 6)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Australia (10 direct), Canada (10 direct), Nigeria (10 direct), Finland (11 direct), and Norway (10 direct), bringing 33 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Central & Southern European Desks Expansion to 10+ Sources (Phase 3 Batch 5)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Serbia (11 direct), Spain (11 direct), Czechia (11 direct), Slovakia (10 direct), and Italy (10 direct), bringing 28 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

- **Southeast Asia Regional Desks Expansion to 10+ Sources (Phase 3 Batch 4)** — **Done 2026-11-10.**
  - Expanded and verified candidate feeds for Thailand (11 direct), Philippines (10 direct), Myanmar (11 direct), Indonesia (11 direct), and Singapore (10 direct), bringing 23 major global and regional desks into full compliance with the 10-source standard.
  - Verified feed reachability with parallel probe (`tools/probe.py`) across all newly integrated publications.

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
  - **Pack Schemas, Mention Regex Word Boundaries & Ambiguous Terms (Audit Fixes #1 & #2)** — **Done 2026-11-12.**
    Standardized 27 non-conforming country packs (`algeria`, `austria`, `baltics`, `bangladesh`, `belgium`, `caribbean`, `central_america`, `chile`, `denmark`, `east_africa`, `ecuador`, `greece`, `iraq`, `ireland`, `jordan`, `lebanon`, `morocco`, `netherlands`, `norway`, `pacific_islands`, `peru`, `portugal`, `romania`, `sri_lanka`, `switzerland`, `syria`, `west_africa`) to standard `pack.yaml` schema (`url_sections.skip`, `excerpt.dateline`, `reddit`); added fallback resolution in `argos/packs.py` and `argos/reddit.py` to prevent silent key drops; implemented Unicode-aware word-boundary wrapping (`_term_regex`) for spaced scripts to eliminate substring collisions (`lac`, `modi`, `rbi`, `mali`, `niger`) while preserving CJK/unspaced matching; disambiguated mentions in India, Lebanon, and Nigeria; added pack schema integrity verification in `tools/audit_sources.py` and unit tests in `tests/test_packs.py`; updated `site/about.html` sampling disclosures.
  - **Leadership Name Refresh & Multilingual Theme Coverage Across 87 Desks (Audit Fixes #3 & #5)** — **Done 2026-11-12.**
    Updated political leadership queries and relevance terms to track current governing figures: added Friedrich Merz and office-based `Bundeskanzler` keywords for Germany; added Ahmed al-Sharaa (Abu Mohammad al-Julani) and transitional governance entities for Syria; updated South Korea (Han Duck-soo, Lee Jae-myung), Peru (Gustavo Adrianzén), and Lebanon. Extended shared `themes.yaml` with core French, Spanish, German, Arabic, and Vietnamese vocabulary across diplomacy, trade, investment, economic policy, governance, defense, and unrest. Created tailored native-language `themes.yaml` packs for all 27 formerly un-themed country desks (`tools/populate_missing_themes.py`), achieving 100% desk theme coverage.
  - **Ranking Rebalancing & Authoritative Representative Selection (Audit Fix #6)** — **Done 2026-11-12.**
    Rebalanced `argos/rank.py` scoring: replaced the disproportionate flat additive theme bonus with a coverage multiplier (`Score = Coverage * (0.6 + 0.5 * Policy) + 1.2 * Policy + Election_Bonus`) and super-linear independent consensus bonuses (+1.0 for 3+ outlets, +2.0 + 0.5*(N-5) for 5+), preventing single-article items with coincidental keyword matches from outranking genuine multi-outlet national news. Overhauled representative article selection in `argos/cluster.py` (`_pick_representative`) to prioritize authoritative domestic newspapers of record over syndicated wire copies or foreign opinion op-eds. Created comprehensive unit tests in `tests/test_rank.py` and updated `site/about.html` methodology.
