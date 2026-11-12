# Decisions

Settled decisions and the reasons for them. Add new decisions at the bottom, with a date.

## 2026-09-30: initial scoping

**D1. Vietnam is the first country.**
It's the user's choice. It also tests the evidence-first idea hardest, because domestic media is state-licensed.

**D2. Coverage is split three ways, not two (local/international).**
- `domestic`: Vietnamese outlets licensed in Vietnam. All of them answer to a Party or state body (VnExpress, Tuổi Trẻ, Thanh Niên, Dân trí, VietnamNet, Nhân Dân, VNA/VietnamPlus, VOV, and their English editions).
- `abroad_vi`: Vietnamese-language outlets outside Vietnam (e.g. BBC Tiếng Việt, RFI Tiếng Việt, Luật Khoa, diaspora press).
- `international`: foreign outlets in other languages (Reuters, Nikkei Asia, The Diplomat, SCMP, …).
The key signal is **stories covered abroad but missing from domestic media**. It replaces the brief's "big locally, not yet international" idea, which matters less for Vietnam.

**D3. Evidence labels have been adapted for Vietnam.**
- `REPORTED`: a media outlet reports it.
- `OFFICIAL`: stated by a government, ministry, Party or National Assembly source. The brief called this "CONFIRMED", but state media and the government are not independent of each other. So this label means "officially stated", not "independently verified".
- `UNVERIFIED`: only in sources that aren't credible or independent. Not used in the MVP, because there is no Social Watch yet.

**D4. The core has no LLM, and its summaries are extractive.**
The user wants free, minimal token use. Summaries are the headline of the most representative article plus 2–3 sentences quoted from different sources. Quoted text traces to its source automatically, so nothing can be hallucinated. An optional LLM layer, used only for the top ~10 stories, may come later and must pass the verbatim-quote check.

**D5. Translation is done by the browser.**
The dashboard shows the original text, and the user uses the browser's translate feature. Possible later step: translate headlines offline with a local `opus-mt-vi-en` model.

**D6. No Social Watch in the MVP.**
Vietnamese discussion lives on Facebook, Zalo and TikTok, and none of them has a usable public API. Later options: YouTube Data API, Google Trends, and possibly Reddit.

**D7. It runs locally, with no server.**
A Python script runs the pipeline and writes a static `dashboard.html`. It is run manually, or later by Windows Task Scheduler. The SQLite database lives outside Google Drive (`C:\ArgosData`).

**D8. Categories come from section feeds first, then embeddings.**
Vietnamese outlets publish RSS per section (Thời sự, Kinh doanh, Thế giới, Pháp luật, …), which gives a category for free. Articles without a useful section are classified by embedding similarity to category descriptions. "Internal politics" in Vietnam mostly means Party personnel, the anti-corruption campaign and Politburo or Central Committee decisions.

**D9. The MVP window is 7 days.**
24h and 30d come later.

**D10. The brief's sections 17–20 are not planning input.**
They're generic viability and QA text. [brief.md](brief.md) is kept for the long-term vision only.

## 2026-09-30: headline translation

**D11. Headlines are shown as a labelled English machine translation next to the original.**
The user finds long Vietnamese titles hard to scan. Each story shows the representative headline in the original language plus a short English translation, marked "machine translation", with the link to the original article. This refines D5 (translation is still never evidence; the original stays visible and authoritative). The app still writes no summaries of its own (rule 1). Translation runs locally through Ollama (`qwen2.5:3b-instruct`, already installed) for the roughly top stories only, and is cached in the database. A 3B model is modest for Vietnamese, so its output must always be labelled and never quoted as a source.

**D11 update (same day): translation is switched off for now.** A test of `qwen2.5:3b-instruct` on 40 dashboard headlines gave wrong English for roughly 1 in 4: a Politburo mix-up for the Viet Tan arrests, an invented "Temple of Heaven", 36,000 billion read as 36 billion, 143.5 million read as 14.35 million, Chinese characters mid-sentence. The user chose to skip translation until a better option exists. The code stays in `argos/translate.py` and the `translation` table exists, but `python run.py` does not run it and the dashboard must not show translations. Options when revisiting: `qwen2.5:7b-instruct` (about 4.7 GB, tight on 8 GB RAM) or `opus-mt-vi-en` (about 300 MB). Until then, headlines are shown in the original language and the reader uses the browser's translate button (as in D5).

## 2026-09-30: interactive website

**D12. The product is a website with three dropdowns and a Research button; it is built local-first.**
The user wants to choose a country, a time period and a topic on a simple page, press "Research", and get a collection of that period's news. Eventually the site should be on the internet. Hosting is undecided: the user chose "start local, decide hosting later". This replaces D7 ("one static dashboard.html, no interaction").
Design that keeps both hosting options open: the pipeline writes precomputed results as data files (one per country and period, with every story carrying its category), and a static page (plain HTML, CSS and vanilla JS, no framework) filters them in the browser when the user presses Research. That page runs from a local folder now and can be published unchanged to a free static host (option A: Cloudflare Pages or GitHub Pages). A rented server (option B) stays possible later because the pipeline does not change.
Rules for anything public: show only headlines, short verified quotes and links to originals, never full article text; full texts stay in the local database.
Limits accepted: only Vietnam is set up (each new country needs its own source list and relevance rules); periods are 24 hours and 7 days at first, 30 days only after the collector has run for a month.

**D11 update 2 (same day): English is shown first, translated by the reader's own browser.**
The user wants English prominent and the Vietnamese secondary. The site now uses the browser's built-in on-device translator (the `Translator` web API in Chrome and Edge on a computer) to turn headlines, quotes and source-list titles into English as they are shown. The app writes, stores and hosts no translation, so rules 1 and 4 and D5 still hold. The original text stays on the page in grey under each English line, and the headline link goes to the original article. The quotes checked against stored article text are still the Vietnamese originals. Where the browser has no translator (Firefox, Safari, probably phones), or before the one-time language download, the page shows the original text with a note. Page notes always say the English is a machine translation. Tested with a stand-in translator only; not yet seen with the real one. `argos/translate.py` (the Ollama route) stays unused.

**D11 update 3 (same day): English only by default.** The user does not want to see Vietnamese on the page. The original Vietnamese lines are now hidden by default; a "Show original Vietnamese" switch on the results page turns them on (remembered in the browser). The switch stays because the English is a machine translation, and the original is how a reader checks a line against the real article. Every headline still links to the original article, and outlet names keep their proper spelling (Tuổi Trẻ). Where the browser cannot translate, the page still has to show the Vietnamese, with a note.

## 2026-09-30: cloud, daily

**D13. The digest is built once a day in the cloud, for free, and published as a static site.**
The user wants a morning digest: pick a country, get the most relevant news for the last 24 hours or 7 days, ready by 7am, running entirely in the cloud at no cost. The likely audience is press-review staff at foreign ministries, so accuracy, source transparency and multiple countries matter. This settles the hosting question in D12 as "option A, in the cloud".
How: a GitHub Actions workflow (`.github/workflows/daily.yml`) runs the unchanged pipeline once a day at 21:00 UTC (04:00 in Vietnam), keeps the database between runs in the Actions cache, and publishes the `site` folder to Cloudflare Pages. About 30 runs of 30 to 40 minutes a month fits the 2,000 free minutes of a private repository. A Cloudflare Worker cannot run the pipeline (128 MB memory, short CPU limits, Python libraries), so it is not used for the refresh.
Go/no-go first: `.github/workflows/probe.yml` (run by hand) checks whether the news sites refuse GitHub's cloud machines. Some already refuse this laptop's home connection at times (Dân trí, VOV), so cloud addresses may be blocked more often. If many outlets fail from the cloud, the fallback is to run the collection on the laptop and publish the result.
Open items: only Vietnam is set up (each country needs its own source list and relevance rules); the public site should be reviewed for the sources' terms of use before official use.

## 2026-10-01: what counts as important

**D14. Ranking weighs policy relevance for a foreign-office reader, not only how widely a story was reported.**
The user described the intended reader: a foreign-ministry press reviewer. What matters most is investment, trade, foreign relations and policy. Individual stories (for example a corruption trial) count only if they signal something policy-wise, such as the anti-corruption drive.
How: `themes.yaml` lists the themes with weights (diplomacy, trade, investment and economic policy 1.0; security 0.9; party and government, anti-corruption drive 0.8; energy and infrastructure 0.7) and low themes (individual crime 0.1, accidents and weather 0.2, sport and entertainment 0.05); unmatched stories get 0.3. `argos/policy.py` tags each story from keywords (a headline match counts fully, a summary-only match 0.3) and, rarely, from embedding similarity. A crime- or accident-flavoured story keeps only the anti-corruption, security and diplomacy tags. The score becomes coverage × (0.4 + 0.8 × policy) + 3 × policy, so a well-covered story with no policy angle falls behind a smaller policy story. The tags are shown on each card so a reader can see why a story ranks.
Known limits: keyword lists are editorial judgement written for Vietnam (they move into the country pack later); a few false tags remain (a gold-price story tagged investment); one event split into several stories splits its score; the keywords do not catch stories whose policy meaning is not in the headline. Revisit after real use.

## 2026-10-01: country packs and Hungary

**D15. Each country is a self-contained pack in `countries/<id>/`; Hungary is the second.**
A pack holds `pack.yaml` (name, language, the words that mean "about this country", excerpt cleanup, topic wording in its language), `sources.yaml` (outlets and feeds) and `themes.yaml` (the country's keywords and descriptions added to the shared `themes.yaml`, plus any theme of its own: Hungary adds "EU, Russia and Ukraine"). The database carries a country on every article and story; every stage works per country; the site lists every pack that has data. Source scopes became `domestic | abroad_local | international` (`abroad_local` is the country's own language, outside the country). A feed address can belong to one pack only.
Rules for any new pack: about 10 to 20 reliable outlets; every outlet verified alive and reachable (see docs/sources.md); ownership and alignment notes marked "(to confirm)" unless checked; no GDELT.
Hungary-specific design: most Hungarian outlets publish one all-topics feed, so the section is read from the first part of the article address (`url_sections` in pack.yaml): world sections need a mention of Hungary, sport and lifestyle sections are skipped. 444 has no section in its addresses, so it can't be filtered that way.
**Collection runs every 3 hours, not once a day.** A feed holds only the latest 30 to 60 items, which a busy outlet fills in a few hours, so one run a day misses most of the day. A normal run takes about 10 minutes and a public repository has unlimited minutes. The page is still ready by 07:00.

**D16. Google News search feeds are used as a news aggregator, headlines only.**
The user accepted headline-only items provided the same story is not counted twice. Each country pack lists Google News search feeds as sources (`aggregator: google_news`). Every item names its outlet; the outlet becomes its own source (`gn:<outlet>`), and `aggregator_outlets` in pack.yaml sorts known outlets into domestic or abroad (anything else takes the default of its feed: international for the English edition, domestic for a local-language edition). The article page is not fetched (`extract_status = nofetch`), so these stories get no quoted sentences. An item whose headline already exists is skipped; identical headlines from different outlets are marked as copies of the first, so a wire story counts once. The Hungarian edition also surfaces headlines from outlets that block us directly (Népszava, Átlátszó, Székelyhon and others). Terms: the feeds are meant for personal use; republishing only headlines and links is low risk but it is not a licensed data source, so it should be reviewed before official use.
The crisis and official feeds (travel advisories, GDACS, Crisis Group) are saved in docs/ideas.md for later.

## 2026-10-12: South Africa pack

**D17. South Africa pack added (`countries/south_africa/`).**
Media in South Africa is predominantly English-language with high press freedom, diverse private media, and official coverage through the public broadcaster (SABC) and GCIS wire (SAnews). Scope `abroad_local` maps to Pan-African and regional African distributors (such as AllAfrica and The Continent). Policy themes are tuned to the Government of National Unity (GNU), Eskom and Transnet state-owned enterprise logistics reforms, and South Africa's global geopolitical posture (BRICS, ICJ litigation, and non-alignment).

## 2026-11-03: Laos and Japan packs

**D18. Laos and Japan packs added (`countries/laos/`, `countries/japan/`).**
- **Laos (`countries/laos/`):** Primary language Lao (`lo`) with bilingual domestic press (The Laotian Times, Vientiane Times, KPL wire) and diaspora/independent reporting via Radio Free Asia Lao. Policy themes capture Mekong River hydropower dam politics and energy export, sovereign debt restructuring with Chinese creditors, the Laos-China railway corridor, and Golden Triangle SEZ crime and scam compound crackdowns.
- **Japan (`countries/japan/`):** Primary language Japanese (`ja`) in the new `East Asia` desk. Media spans independent national dailies (The Japan Times, Mainichi Shimbun, Asahi Shimbun), national wires (Kyodo News via Google News), business press (Nikkei Asia), and international Japanese-language coverage (BBC News Japan, Newsweek Japan). Policy themes focus on Shigeru Ishiba's government and Diet politics, Bank of Japan (BOJ) monetary policy and yen dynamics, semiconductor security (Rapidus, TSMC Kumamoto), defense expansion (2% GDP target, counterstrike capabilities, Okinawa), and demographic aging.

## 2026-11-03: South Korea and Taiwan packs (completing East Asia desk)

**D19. South Korea and Taiwan packs added (`countries/south_korea/`, `countries/taiwan/`).**
- **South Korea (`countries/south_korea/`):** Primary language Korean (`ko`) in `East Asia`. Sources combine statutory national wire Yonhap (English & Korean), independent national press (The Korea Times, Dong-A Ilbo), diaspora broadcasting (BBC Korean, RFA Korean), and Google News aggregators. Policy themes focus on Yoon Suk Yeol administration and National Assembly politics, Bank of Korea monetary policy and KRW dynamics, semiconductor memory supply chain (Samsung, SK Hynix HBM), defense exports (K-defense), North Korean nuclear/missile deterrence and troop dispatch to Russia, and medical quota disputes.
- **Taiwan (`countries/taiwan/`):** Primary language Traditional Chinese (`zh`) in `East Asia`. Sources feature leading English daily Taipei Times, premier national daily Liberty Times (Chinese Politics & Business feeds), national wire CNA / Focus Taiwan via Google News, and diaspora reporting. Policy themes center on Lai Ching-te administration and Legislative Yuan gridlock, TSMC advanced 2nm silicon shield and AI hardware supply chain, Taiwan Strait defense and PLA deterrence (ADIZ incursions, Hai Kun submarines), and energy transition.

## 2026-11-03: retirement of automated blind-spot detection

**D20. Automated blind-spot detection retired in favor of transparent source-scope composition.**
The binary `abroad_only` ("Not in domestic press") flag proved unreliable across 32 countries for two reasons: (1) cross-lingual cluster fractures—when domestic press reports an event in the local language (e.g. Turkish, Portuguese, Vietnamese) and international press reports it in English, embedding models frequently placed them in separate clusters, falsely stamping mainstream events (such as Lula's election in Brazil or Kurdish peace process developments in Turkey) as 'Not in domestic press'; (2) proving a negative from an RSS sample violates Rule 1 ('No source, no statement'). Furthermore, true exile/diaspora media only exists for a handful of countries (Vietnam, Myanmar, Cambodia). The automated flag and Home section are retired. Instead, stories retain truthful `by_scope` metrics (`domestic`, `abroad_local`, `international`), allowing analysts to inspect the source distribution directly in the story drawer without the system making unverified claims of censorship.

## 2026-11-03: Czechia country pack (completing Visegrad Four - V4)

**D21. Czechia pack added (`countries/czechia/`), completing the Visegrad Four (V4) desk.**
- **Czechia (`countries/czechia/`):** Primary language Czech (`cs`) in `Central Europe`. Sources combine independent investigative dailies (Deník N, Seznam Zprávy, Novinky.cz), English reporting (Prague Morning), Czech Public Radio (iROZHLAS), state wire ČTK / public television ČT24 via Google News, and Slovak regional coverage. Policy themes capture Petr Fiala SPOLU coalition governance vs. Andrej Babiš ANO opposition, the Czech artillery ammunition initiative for Ukraine, Dukovany nuclear power plant expansion (KHNP contract), and V4 diplomatic divergence between Prague/Warsaw and Bratislava/Budapest.

## 2026-11-03: political alignment, editorial leaning, and perspective analysis

**D22. Source political alignment, editorial leaning, and factuality integration.**
To move beyond generic outlet lists toward actionable media-intelligence analysis, Argos integrates structured rating taxonomy across domestic, regional, and international media:
- **Taxonomy:**
  - `alignment`: `state_controlled`, `pro_government`, `public_broadcaster`, `independent`, `opposition`, `unrated`
  - `bias`: `left`, `center-left`, `center`, `center-right`, `right`, `state_aligned`, `unrated`
  - `factuality`: `very_high`, `high`, `mostly_factual`, `mixed`, `unrated`
- **Data & Ingestion (`argos/ratings.py`, `argos/db.py`, `argos/ingest.py`):**
  - Ratings cover international wires, global broadcasters, and domestic publishers across all monitored desks, with structural fallbacks based on `state_affiliated` flags and outlet kind. Precompiled regex matching evaluates 2,000+ sources in 0.3s.
  - `source` table schema expanded with `bias`, `alignment`, `factuality` columns; `reconcile_ratings(db)` auto-populates ratings across all registered and aggregator sources.
- **Story Export (`argos/export.py`):**
  - Computes story-level perspective metrics: `state_share` (share of sources that are state-controlled or pro-government), plus distribution counters for `alignment` and `bias`.
  - Attaches source-level alignment, bias, and factuality tags to all listed articles.
- **UI Presentation (`site/app.js`, `site/about.html`):**
  - Story cards/drawers display perspective badges (`State-Dominated`, `State & Indep`, `Cross-Spectrum`, `Independent`) and detailed perspective breakdowns.
  - Story drawer lists show compact affiliation/bias chips (`[State · State-aligned]`, `[Public · Center-Left]`, `[Indep · Center]`) with hover tooltips for factuality ratings.
  - About page directory includes filterable `Alignment`, `Editorial Leaning`, and `Factuality` columns across all monitored desks.

## 2026-11-03: retirement of heuristic violence taxonomy in favor of sensor/advisory model

**D23. Transition to verified sensor and official advisory model for conflict & security monitoring.**
The experimental "ACLED-style" violent event classifier (introduced in f83eb72) applied broad multilingual regexes across general news headlines. This produced severe false positives and directly violated Rule 1 (*No source, no statement*):
1. **Administrative & Diplomatic Misclassifications:** Routine military leadership handovers (e.g. Border Guard Artillery-Missile command handovers) were stamped `EXPLOSION & STRIKE` simply because weapon unit nouns appeared in administrative texts; bilateral defense diplomacy (e.g. Vietnam-Japan defense cooperation) was stamped `ARMED CLASH & BATTLE`.
2. **Cross-Language Polysemy & Normalization Collisions:** Polish mold cleaning (*różowy nalot*) was tagged as an air raid (*nalot*); frontend diacritic stripping turned Vietnamese `cảnh báo` / `thông báo` into `bao`, colliding directly with `bão` and tagging consular embassy alerts as `STORM & CYCLONE`.
3. **Absence of Real ACLED 24/7 Access:** Real ACLED data is human-curated and delayed by a week on the open tier; commercial enterprise platforms (Crisis24, GardaWorld) offer no public feeds. Simulating ACLED by heuristic guessing on RSS feeds invented claims of violence where none occurred.

**Architecture under D23 (Option A):**
- **Retired:** `VIOLENCE_RULES` regexes, synthetic tactical badges (`EXPLOSION & STRIKE`, `ARMED CLASH & BATTLE`), and client-side violent event keyword guessing.
- **Fixed:** Vietnamese storm regex in `DISASTER_RULES` now explicitly requires compound patterns (`siêu bão`, `áp thấp`, `lốc xoáy`, `cơn bão`), preventing `cảnh báo` / `thông báo` collisions.
- **Verified Sensor & Advisory Layer:** Conflict and security tracking is anchored in verified external feeds: US Department of State (Levels 2–4), UK FCDO foreign travel advice, and International Crisis Group conflict briefs, alongside existing GDACS, USGS, and NASA EONET feeds.
- **Truthful Press Coverage:** The Conflict & Security view surfaces genuine story clusters classified into `defence_security` by section feeds and embeddings, preserving original headlines without synthetic tactical badges.

## 2026-11-03: zero-emoji policy and delta comparisons specification

**D24. Strict zero-emoji policy for diplomatic broadsheet aesthetic and data hygiene.**
Argos Monitor is built for foreign-ministry press review and institutional analysis. Emojis diminish the seriousness of diplomatic monitoring, introduce unpredictable font rendering, and break character-width grid alignment.
- **Rules:** Exactly 0 emojis across the entire project (UI, badges, alerts, documentation, commit messages, and metadata).
- **Ingestion Hygiene:** `clean()` in `argos/textutil.py` strips all SMP pictographs, dingbats, and emoji variation selectors from incoming RSS headlines and leads so third-party feed formatting cannot leak into the broadsheet interface.
- **Visual Vocabulary:** Visual distinctions use restrained broadsheet typography: bordered text pills (`[NEW]`, `[SURGE +12]`, `[OFFICIAL]`, `[INTL PICKUP]`), ISO mathematical arrows (`↑`, `↓`), and integer counts (`+14`).

**D25. Deterministic delta comparison architecture ("What changed?") between time windows.**
Following section 10 of the product brief, analysts require direct visibility into news cycle momentum rather than static cumulative volume.
- **Window Slicing:** For any active window $T$ (e.g. 24h or 7d), compare against the preceding contiguous window $T_{-1}$ of identical duration ($[now - 2 \cdot W, now - W]$).
- **Story Movement Metrics:**
  - `state`: `new` ($T_{-1} = 0, T \ge 2$), `surging` ($T - T_{-1} \ge 3$ and $T / T_{-1} \ge 1.75$), `cooling` ($T_{-1} - T \ge 3$ and $T / T_{-1} \le 0.4$), `steady` (consistent volume), or `trace` ($< 2$ articles).
  - `net`: integer difference $T - T_{-1}$.
  - `ratio`: $T / \max(T_{-1}, 1)$ rounded to 1 decimal place.
  - `scope_escalation`: flags stories whose $T_{-1}$ coverage was exclusively `domestic` but whose $T$ window incorporates `international` or `abroad_local` reporting (`international_pickup`).
- **Macro Agenda Delta:**
  - Net category volume change ($\Delta N$) and percentage-point share shifts ($\Delta S$) across the 6 core policy categories.
- **Perspective Delta:**
  - Tracks shifts in state-affiliated media share ($\Delta \text{state\_share}$) to flag narrative surges or sudden state silence.
- **Zero-LLM & Evidence Integrity:**
  - All delta metrics are computed deterministically in SQLite during export and embedded in the static `.json` export bundles. Every movement badge links to the verified underlying article cluster. Detailed schema in `docs/delta_spec.md`.

## 2026-11-12: schedule frequency optimization

**D28. Revert automated workflow schedule from every 3 hours to once daily at 21:17 UTC.**
With 87 country desks expanded to 10+ sources each (~1,000 feeds, full text extraction, ONNX embeddings, and clustering), running every 3 hours caused runner minute exhaustion on GitHub Actions and excessive workflow duration. Switching to a single daily execution at 21:17 UTC (04:17 Indochina Time / 22:17 CET) preserves the 2,000 monthly runner quota, guarantees a fresh brief ready before 07:00 local time, and avoids runner timeouts.

**D29. Title and lead priority over heavy full-text scraping.**
Across 87 country desks and 1,370+ feeds, polling feeds ingests thousands of articles per day. Every standard feed natively supplies the article's `title`, publisher `lead` / summary, canonical URL, and publication timestamp.
- **Title + Lead as Primary Operational Unit:** Multilingual dense embeddings (`intfloat/multilingual-e5-small`), cosine clustering, hierarchical category classification, and policy-theme ranking all operate completely on `title` + `lead`.
- **Targeted Full-Text Scraping:** Full-text scraping (via Trafilatura) is restricted exclusively to articles that have clustered into active dashboard stories (`ARGOS_EXTRACT_STORY_ONLY=1`) and capped at 250 articles globally. This eliminates 98% of web scraping requests, cuts pipeline duration from 2.5+ hours to under 10 minutes, and prevents runner timeouts.
- **Evidentiary Resilience:** If an article's full HTML cannot be scraped (e.g. anti-bot paywalls or timeout), the story remains fully formed, clustered, and displayed with its verbatim headline and publisher lead.





