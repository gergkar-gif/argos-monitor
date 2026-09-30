# Original product brief

> This is the original handover brief, kept word for word. It describes the **long-term vision**. MVP scope and changes for Vietnam are in [decisions.md](decisions.md). Where the two conflict, decisions.md wins.

## 1. Product concept
Build a news-monitoring and country/topic intelligence web app. The user enters a country or topic and selects a monitoring period. The application retrieves relevant news across multiple languages, clusters duplicate coverage into stories, organises developments into major subject areas, and provides a separate social-media monitoring layer.

The product is intended to answer: What has happened around this country/topic during this period, how is it being reported locally and internationally, and what is gaining attention on social media?

## 2. Core user controls
- Country and/or topic.
- Time period: last 24 hours, last 7 days, last 30 days, with a possible custom date range later.
- Source scope: all, local, international, primary sources.
- Language filter: all or selected languages.

## 3. Main dashboard
- Executive overview: approximately 5-10 significant developments.
- Internal politics: government, opposition, elections, legislation, protests, political controversies.
- Economics: inflation, GDP, currency, markets, companies, trade, economic policy.
- Foreign policy: bilateral relations, EU/NATO/UN activity, diplomacy and international disputes.
- Defence & security: military, intelligence, terrorism, cyber, borders and security incidents.
- Society: demographics, education, healthcare and major social issues.
- Other: significant developments that do not fit the main categories.
- Social Watch: separate monitoring of trends, controversies, emerging stories and narratives.

## 4. Story clustering
The application should cluster multiple articles covering the same underlying development into a single story. The user should see the story once, with the number and composition of sources visible.

Example: Coverage 14 sources: 8 Hungarian, 3 English, 2 German, 1 Romanian.

Do not treat translated or syndicated versions of the same event as independent developments.

Retain every original article as a separate source record.

## 5. Source traceability and anti-hallucination requirement
This is a hard architectural requirement. Every factual statement shown to the user must be traceable to one or more retrieved sources.

No source, no factual statement.

AI-generated summaries must reference source IDs internally.

The system should not generate a summary first and search for supporting evidence afterwards.

Source claims should be checked against the retrieved material before being displayed.

Users must be able to open the underlying source article.

Primary sources should be distinguished from media reporting.

The system should preserve an audit trail showing which sources support each claim.

Recommended internal structure:
`claim = {"text": "...", "source_ids": ["12345", "12351"]}`

## 6. Evidence categories
- REPORTED: A news organisation reports the event or claim.
- CONFIRMED: A relevant primary source independently confirms it.
- UNVERIFIED / CLAIM: The claim is circulating but independent confirmation has not been found.

Social-media claims must never automatically become factual statements. For example, if users claim that a minister resigned but no ministry, government or reputable media source confirms it, the system should label it as an unverified claim.

## 7. Multilingual sourcing
Multilingual local sourcing is a core feature. The system should not be an English-language search engine with translation added afterwards.
- Prioritise local-language news for each country.
- Also retrieve international and regional coverage.
- Retrieve primary sources in the relevant local language.
- Monitor relevant local-language social media.
- Use translation for cross-language analysis and user comprehension, while retaining the original source and language.
- The original article remains the authoritative source; an AI translation is not itself evidence.

Country configuration should define relevant local languages. Examples: Hungary -> Hungarian; Vietnam -> Vietnamese; Belgium -> Dutch/French; Switzerland -> German/French/Italian/Romansh.

## 8. Local vs international perspective
Each major story should expose the composition of its coverage.
- Local coverage.
- International coverage.
- Regional coverage where relevant.
- Primary sources.
- Social discussion.

This allows the user to identify stories that are already significant locally but have not yet received international coverage.

## 9. Social Watch
Social Watch should be a dedicated intelligence layer rather than simply a social-media feed.
- Emerging stories.
- Trending subjects and hashtags.
- Major controversies/scandals.
- Rapidly increasing discussion volume.
- Political/public narratives.
- Relevant people and organisations.
- Platform/source attribution.
- Local-language social discussion.

A key metric should be change in attention over time, not simply total mentions. For example, a topic rising from 300 to 12,000 mentions may be more important than a topic that has remained at a stable high level.

## 10. 'What changed?' mode
A useful future feature is a comparison against the previous equivalent period.
- Coverage volume change.
- New major stories.
- Topics gaining or losing attention.
- Changes in social-media activity.
- New international attention to previously local stories.

## 11. Saved watches
Users should eventually be able to save recurring country/topic watches, for example:
- Hungary - 24h / 7d / 30d
- Vietnam - 24h / 7d
- EU migration policy - 7d
- China - 24h

A later feature could generate a morning brief from the underlying structured story database.

## 12. Suggested technical architecture
A relatively lightweight architecture is sufficient for an MVP.
- Frontend: lightweight web application; vanilla HTML/CSS/JavaScript is sufficient for an initial version.
- Backend: small Python or Node.js service.
- Database: PostgreSQL or SQLite for an early prototype.
- Scheduled ingestion pipeline.
- News/source ingestion.
- Deduplication and cross-language story clustering.
- Topic/category classification.
- Evidence-linked AI summarisation.
- Social signal processing.

Conceptual pipeline:
USER WATCH → NEWS / SOCIAL / PRIMARY SOURCES → INGESTION → DEDUPLICATION → STORY CLUSTERING → CLASSIFICATION → EVIDENCE-LINKED AI ANALYSIS → DASHBOARD

## 13. Potential data sources
GDELT is a promising starting point for international news discovery, article search, timelines and story/event clustering. It should be supplemented with RSS feeds, national media, primary-source feeds and other APIs as needed.
- International news databases/APIs.
- RSS feeds from national and international publishers.
- Government and ministry websites.
- Parliamentary feeds.
- Central banks and statistical offices.
- EU/NATO/UN and other institutional sources.
- Social platforms and accessible public data sources.

## 14. MVP scope
Do not attempt to monitor the entire internet and every social network initially.
- Country/topic input.
- 24h / 7d / 30d periods.
- News clustering.
- Internal politics, economics, foreign policy, defence & security, society and other categories.
- Multilingual/local-language sourcing.
- Evidence-linked summaries.
- Full source list for every story.
- Basic Social Watch using accessible sources.

A sensible initial test set would include several countries with different media/language environments, such as Hungary, Vietnam, Poland, Ukraine and South Africa.

## 15. Non-negotiable product principles
- Evidence first.
- Every factual statement must have source provenance.
- Local-language reporting is first-class information, not an optional translation layer.
- Original sources remain accessible.
- AI summarises and organises retrieved evidence; it does not act as an independent source of facts.
- Social-media claims are clearly separated from confirmed reporting.
- Multiple independent sources should be visible rather than collapsed into an opaque AI answer.
- The interface should make it easy to inspect the evidence behind a story.

## 16. One-sentence product definition
A multilingual, evidence-first news intelligence dashboard that lets users monitor any country or topic over a chosen period, organises developments by subject, compares local and international coverage, and separately tracks emerging social-media narratives.

## 17–20. (Omitted)
The original brief also had sections on Project Viability Assessment, Quality Assurance Strategy, Compliance and Legal Considerations, and a Post-MVP Roadmap. They were generic, and decision D10 excludes them from planning. The relevant parts are covered in [roadmap.md](roadmap.md) (Phase 2) and [architecture.md](architecture.md) (legal and ethics).
